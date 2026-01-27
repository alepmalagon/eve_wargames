# livekit_events.py
import pprint
import json
import asyncio
import random
from datetime import datetime
from functools import partial
import os
import requests

# Import necessary types and classes used within the handlers
import agent.utils
from livekit import api
from livekit.agents import JobContext, metrics as lk_metrics, get_job_context
from livekit.agents.voice import MetricsCollectedEvent
from livekit.agents.metrics import VADMetrics, STTMetrics, TTSMetrics, LLMMetrics, EOUMetrics, RealtimeModelMetrics
from livekit.agents.voice.events import CloseEvent
from agent.utils.utils import serialize_payload_events
from agent.utils.metrics import CallData
from agent.config import WAIT_PHRASES, USER_IDLE_PHRASES
import agent.api.api_client_setup

max_idle_prompts = int(os.getenv("MAX_USER_IDLE_PROMPTS", 3))

# Import logger
from agent.utils.logging_setup import logger

from agent.utils.logging_setup import (
    LOG_LIFECYCLE,
    LOG_EVENTS,
    LOG_IDLE_CHECKS,
    LOG_METRICS_VERBOSE,
    LOG_FUNCTION_CALLS,
    LOG_CONVERSATION,
    LOG_STATE_CHANGES
)

# Global variables moved to context object (ctx_obj) for better state management

def init_metrics_variables(ctx_obj: dict):
    """
    Initialize metrics variables in the context object if they don't exist.
    This ensures all handlers have access to the required metrics state.
    """
    if "end_of_utterance_delay" not in ctx_obj:
        ctx_obj["end_of_utterance_delay"] = 0
    if "ttfb_dict" not in ctx_obj:
        ctx_obj["ttfb_dict"] = 0
    if "ttft_dict" not in ctx_obj:
        ctx_obj["ttft_dict"] = 0
    if "transcription_delay" not in ctx_obj:
        ctx_obj["transcription_delay"] = 0
    if "speech_id" not in ctx_obj:
        ctx_obj["speech_id"] = 'not set'

async def hangup_call(ctx_obj):
    ctx = ctx_obj.get("ctx", None)
    if ctx is None:
        # Not running in a job context
        if LOG_LIFECYCLE:
            logger.info(f" Not running in a job context")
        return
    if LOG_LIFECYCLE:
        logger.info(f"Deleting room {ctx.room.name}")

    await ctx.api.room.delete_room(
        api.DeleteRoomRequest(
            room=ctx.room.name,
        )
    )

async def _idle_timeout_check(ctx_obj: dict, user_utterance_timestamp: datetime):
    """
    Waits for the configured timeout, then if the assistant
    hasn't replied since user_utterance_timestamp, issues a "please wait" prompt.
    This is for when the agent is taking too long to respond to the user.
    """
    # get timeout (in seconds) from config, defaulting to 18
    timeout = ctx_obj["agent_config_data"].get("response_timeout", 18)
    if LOG_IDLE_CHECKS:
        logger.info(f" Agent response timeout is {timeout} secs")
    await asyncio.sleep(timeout)

    # Fetch the last time agent started speaking from the context
    last_agent_speak_time: datetime = ctx_obj.get("last_agent_time")

    if LOG_IDLE_CHECKS:
        logger.info(
            f" Agent response idle check: Last agent speak time: {last_agent_speak_time}, "
            f" User utterance time: {user_utterance_timestamp}"
        )

    # If assistant started speaking after or at the same time as the user's last utterance,
    # it means the agent is responding (or has responded) to this user utterance.
    if last_agent_speak_time and last_agent_speak_time >= user_utterance_timestamp:
        if LOG_IDLE_CHECKS:
            logger.debug(f" Agent has responded or is responding. No agent idle prompt needed.")
        return

    # Else, agent has not spoken in response to the user's last utterance within the timeout
    lang = ctx_obj["agent_config_data"].get("language", "en")
    phrase_list = WAIT_PHRASES.get(lang, WAIT_PHRASES["en"])
    if LOG_IDLE_CHECKS:
        logger.info(f" Agent response language is {lang}")
    prompt = random.choice(phrase_list)

    session = ctx_obj.get("session")
    if session:
        if LOG_IDLE_CHECKS:
            logger.info(f" No assistant reply within {timeout} for utterance at {user_utterance_timestamp}; prompting user with: {prompt}")
        await session.say(prompt)
    else:
        if LOG_IDLE_CHECKS:
            logger.warning(f" Agent response idle-timeout triggered but no session available to say prompt.")


# --- NEW: Function for user idle timeout check ---
async def _user_idle_timeout_check(ctx_obj: dict, agent_utterance_end_timestamp: datetime):
    """
    Triggered when user is 'away'. 
    Loops and nudges the user at intervals until they speak or max prompts reached.
    """
    timeout = ctx_obj["agent_config_data"].get("user_idle_timeout", 15)
    max_idle = ctx_obj["agent_config_data"].get("max_idle_prompts", 3)
    
    # We loop until we either hang up or the user speaks
    while ctx_obj["consecutive_user_idle_prompts"] < max_idle:
        
        await asyncio.sleep(timeout)

        last_user_speak_time = ctx_obj.get("last_user_utterance_time")
        if last_user_speak_time and last_user_speak_time >= agent_utterance_end_timestamp:
            if LOG_IDLE_CHECKS:
                logger.info("User responded. Breaking idle loop.")
            ctx_obj["consecutive_user_idle_prompts"] = 0
            return 

        ctx_obj["consecutive_user_idle_prompts"] += 1
        current_count = ctx_obj["consecutive_user_idle_prompts"]

        session = ctx_obj.get("session")
        if not session:
            return

        if current_count >= max_idle:
            if LOG_IDLE_CHECKS:
                logger.warning(f"Limit {max_idle} reached. Hanging up.")
            
            hangup_msg = ctx_obj["agent_config_data"].get("hangup_message", "Goodbye!")
            try:
                await session.say(hangup_msg)
                await asyncio.sleep(8) 
            except:
                pass
            await hangup_call(ctx_obj)
            return # Exit after hangup
        
        else:
            # Say a nudge phrase
            lang = ctx_obj["agent_config_data"].get("language", "en")
            phrase_list = USER_IDLE_PHRASES.get(lang, USER_IDLE_PHRASES["en"])
            prompt = random.choice(phrase_list)
            
            if LOG_IDLE_CHECKS:
                logger.info(f"Idle nudge {current_count}/{max_idle}: {prompt}")
            
            await session.say(prompt)


def conversation_item_added_handler(msg, ctx_obj: dict):
    # Initialize metrics variables if they don't exist
    init_metrics_variables(ctx_obj)
    #try:
    item = msg.item

    message_content = item.content
    segment_id = item.id
    item_timestamp = datetime.now() # Timestamp for when this item is processed

    if item.role == "assistant":
        # start_time here is when the agent *started* speaking, from agent_started_speaking_event_handler
        start_time = ctx_obj.get("agent_start_time", item_timestamp)
        if LOG_CONVERSATION:
            logger.info(f" Agent started speaking")
        now = datetime.now()
        # Used by conversation_item_added_handler for logging the agent's turn
        # ctx_obj["ongoing_conversations"]["agent"] = {"start_time": now}
    elif item.role == "user":
        ctx_obj["last_user_utterance_time"] = datetime.now()
        # start_time here is when the user *started* speaking, from user_started_speaking_handler
        start_time = ctx_obj.get("user_start_time", item_timestamp)
        # This timestamp is crucial: it's the reference point for the agent response idle check.
        user_utterance_finalized_time = item_timestamp
        if LOG_CONVERSATION:
            logger.debug(f" Scheduling agent response idle timeout check relative to user utterance finalized at {user_utterance_finalized_time}")
        asyncio.create_task(_idle_timeout_check(ctx_obj, user_utterance_finalized_time))
    if start_time==None:
        start_time = item_timestamp # Fallback for other roles

    # end_time = item_timestamp # The "end_time" for logging this item is when it's processed
    #end_of_utterance_delay_dict = {}
    #ttfb_dict = {}
    #ttft_dict = {}

    #logger.debug(f"TTFB for this user's turn {segment_id} is {ttfb_dict.get('segment_id',0)}")
    #logger.debug(f"TTFT for this user's turn {segment_id} is {ttft_dict.get('segment_id',0)}")
    #logger.debug(f"end_of_utterance_delay for this user's turn {segment_id} is {end_of_utterance_delay_dict.get('segment_id',0)}")
    call_data: CallData = ctx_obj["call_data"]
    call_data.add_log_entry(
        participant_identity=item.role,
        text=message_content,
        start_time=start_time, # When the speech/action began
        end_time=item_timestamp,     # When the item was processed/logged
        segment_id=segment_id,
        end_of_utterance_delay=ctx_obj["end_of_utterance_delay"],
        ttfb=ctx_obj["ttfb_dict"],
        ttft=ctx_obj["ttft_dict"],
        latency=ctx_obj["end_of_utterance_delay"]+ctx_obj["ttfb_dict"]+ctx_obj["ttft_dict"],
        language=ctx_obj["agent_config_data"].get("language", "en"),
        transcription_delay=ctx_obj["transcription_delay"]
    )
    if LOG_CONVERSATION:
        logger.info(f" Conversation Item Added: Role={item.role}, ID={item.id} - Item Content: {item.content} - Latency data: EOU {ctx_obj['end_of_utterance_delay']} TTFB {ctx_obj['ttfb_dict']} TTFT {ctx_obj['ttft_dict']} Latency {ctx_obj['end_of_utterance_delay']+ctx_obj['ttfb_dict']+ctx_obj['ttft_dict']} API_ID {ctx_obj['speech_id']}")
    # Reset metrics variables for next conversation item
    ctx_obj["end_of_utterance_delay"] = 0
    ctx_obj["ttfb_dict"] = 0
    ctx_obj["ttft_dict"] = 0
    ctx_obj["transcription_delay"] = 0

    #except AttributeError as ae:
    #    logger.error(f" Atribute error - {ae} - in message - {msg}")
    #except Exception as e:
    #    logger.error(f" Error processing conversation_item_added event: {e}", exc_info=True)


def metrics_collected_handler(event: MetricsCollectedEvent, ctx_obj: dict):
    # Initialize metrics variables if they don't exist
    init_metrics_variables(ctx_obj)
    actual_metrics = event.metrics
    usage_collector: lk_metrics.UsageCollector = ctx_obj["usage_collector"]
    metrics_batch: list = ctx_obj["metrics_batch"]

    usage_collector.collect(actual_metrics)

    timestamp = getattr(actual_metrics, "timestamp", None)
    sequence_id = getattr(actual_metrics, "sequence_id", None)

    stt_audio_duration = None
    end_of_utterance_delay = None
    transcription_delay = None
    tts_ttfb = None
    tts_duration = None
    tts_audio_duration = None
    stt_duration = None
    llm_duration = None
    llm_ttft = None
    llm_tokens_per_second = None
    speech_id = None
    metrics_type = type(actual_metrics).__name__
    speech_id = getattr(actual_metrics, "speech_id", None)
    ctx_obj["speech_id"] = speech_id
    seen = ctx_obj.setdefault(f"seen_log_entries_{metrics_type}", set())
    if speech_id is not None:
        if speech_id in seen:
            if LOG_METRICS_VERBOSE:
                logger.debug(f" Discarded metric entry  - {pprint.pformat(actual_metrics)}")
            return
        seen.add(speech_id)

    if LOG_METRICS_VERBOSE:
        if actual_metrics.type!="vad_metrics":
            logger.debug(f" Metric entry - {pprint.pformat(actual_metrics)}")

    if isinstance(actual_metrics, STTMetrics):
        stt_audio_duration = getattr(actual_metrics, "audio_duration", None)
        stt_duration = getattr(actual_metrics, "duration", None)
    elif isinstance(actual_metrics, TTSMetrics):
        speech_id = getattr(actual_metrics, "speech_id", None)
        request_id = getattr(actual_metrics, "request_id", None)
#        if speech_id == None: # discard the duplicated metrics that are sent without speech_id
#            return
        tts_ttfb = getattr(actual_metrics, "ttfb", None)
        if tts_ttfb>=0:
            ctx_obj["ttfb_dict"] += tts_ttfb
        tts_duration = getattr(actual_metrics, "duration", None)
        tts_audio_duration = getattr(actual_metrics, "audio_duration", None)
        if LOG_METRICS_VERBOSE:
            logger.info(f" TTFB {tts_ttfb}")
    elif isinstance(actual_metrics, LLMMetrics):
        speech_id = getattr(actual_metrics, "speech_id", None)
#        if speech_id == None: # discard the duplicated metrics that are sent without speech_id
#            return
        llm_duration = getattr(actual_metrics, "duration", None)
        llm_ttft = getattr(actual_metrics, "ttft", None)
        ctx_obj["ttft_dict"] += llm_ttft
        if LOG_METRICS_VERBOSE:
            logger.info(f" TTFT {llm_ttft}")
        llm_tokens_per_second = getattr(actual_metrics, "tokens_per_second", None)
    elif isinstance(actual_metrics, EOUMetrics):
        llm_duration = getattr(actual_metrics, "duration", None)
        speech_id = getattr(actual_metrics, "speech_id", None)
        end_of_utterance_delay = getattr(actual_metrics, "end_of_utterance_delay", None)
        transcription_delay = getattr(actual_metrics, "transcription_delay", None)
        ctx_obj["end_of_utterance_delay"] += end_of_utterance_delay
        ctx_obj["transcription_delay"] += transcription_delay
        if LOG_METRICS_VERBOSE:
            logger.info(f" EoUD {end_of_utterance_delay}")
            logger.info(f" Transcription delay {transcription_delay}")
    elif isinstance(actual_metrics, RealtimeModelMetrics):
        llm_duration = getattr(actual_metrics, "duration", None)
        llm_ttft = getattr(actual_metrics, "ttft", None)

    if not isinstance(actual_metrics, VADMetrics): # we dont want to register VAD metrics, too verbose
        metrics_data = {
            "type":metrics_type,
            "speech_id": speech_id,
            "timestamp": timestamp,
            "identifier": sequence_id or getattr(actual_metrics, "request_id", None) or getattr(actual_metrics, "id", None),
            "type": type(actual_metrics).__name__,
            "end_of_utterance_delay": end_of_utterance_delay,
            "transcription_delay": transcription_delay,
            "ttfb": tts_ttfb,
            "stt_audio_duration": stt_audio_duration,
            "tts_audio_duration": tts_audio_duration,
            "tts_duration": tts_duration,
            "stt_duration": stt_duration,
            "llm_duration": llm_duration,
            "ttft": llm_ttft,
            "llm_tokens_per_second": llm_tokens_per_second
        }
        metrics_batch.append(metrics_data)

def function_calls_finished_handler(called_functions, ctx_obj: dict):
    if LOG_FUNCTION_CALLS:
        logger.debug(f" Functions called {pprint.pformat(called_functions)}")
    if not called_functions:
        return

    func_name = called_functions.function_calls[0].name
    if LOG_FUNCTION_CALLS:
        logger.info(f" Function '{func_name}' finished execution.")

    if func_name.startswith("skill_call_operator_"):
        try:
            call_id = int(func_name.split("_")[-1])  # extract DB ID
        except ValueError:
            logger.error(f"Invalid function name format: {func_name}")
            return

        transfer_calls = ctx_obj.get("transfer_calls", [])
        logger.debug(f"Transfer calls - {pprint.pformat(transfer_calls)}")
        call_cfg = next((c for c in transfer_calls if c["id"] == call_id), None)

        if not call_cfg:
            logger.error(f"No transfer call config found for id {call_id}")
            return
        operator_number = call_cfg.get("operator_number")
        takeover_message = call_cfg.get("take_over_message", "Transferring you now.")

        if not operator_number:
            logger.warning(f"Operator transfer skill {call_id} called, but no operator_number configured.")
            return

        if LOG_FUNCTION_CALLS:
            logger.info(f" Operator skill {call_id} called. Preparing transfer to {operator_number}.")
            logger.info(f" Takeover message: '{takeover_message}'")

        transfer_func = ctx_obj["transfer_func"]

        async def handle_transfer_task():
            if LOG_FUNCTION_CALLS:
                logger.info(f" Executing transfer task for operator {operator_number}.")

            #session = ctx_obj.get("session")
            #if session and takeover_message:
            #    await session.say(takeover_message)
            transfer_delay_after_message = call_cfg.get("transfer_delay_after_message", 5)
            await asyncio.sleep(transfer_delay_after_message)
            if LOG_FUNCTION_CALLS:
                logger.info(f" Transfer delay of {transfer_delay_after_message} secs awaited")

            try:
                await transfer_func(operator_number=operator_number)
                logger.info(f"Transfer to {operator_number} completed.")
            except Exception as e:
                logger.error(f"Error during transfer execution: {e}", exc_info=True)
    elif func_name.startswith("hangup_"):
        hangup_message = ctx_obj["agent_config_data"].get("hangup_message", "Hanging up.")
        async def perform_hangup():
            try:
                session = ctx_obj.get("session")
                if session and hangup_message:
                    session.say(hangup_message)
                    await asyncio.sleep(10) 
            except Exception as e:
                logger.warning(f"Hangup message failed: {e}")
                    
            await hangup_call(ctx_obj)

        asyncio.create_task(perform_hangup())
        hangup_call(ctx_obj)

async def shutdown_hook_logic(ctx_obj: dict):
    job_id = ctx_obj.get("job_id", None)
    if LOG_LIFECYCLE:
        logger.info(f" Shutdown hook initiated.")
    skills = ctx_obj["skills_list"]    
    call_data: CallData = ctx_obj["call_data"]
    usage_collector: lk_metrics.UsageCollector = ctx_obj["usage_collector"]
    metrics_batch: list = ctx_obj["metrics_batch"]
    fast_api_client = ctx_obj["fast_api_client"]
    call_data.status = "Ended"
    summary = usage_collector.get_summary()
    if LOG_METRICS_VERBOSE:
        logger.info(f" Usage Collector Summary:\n{pprint.pformat(summary)}")

    call_data.llm_prompt_tokens = summary.llm_prompt_tokens
    call_data.llm_completion_tokens = summary.llm_completion_tokens
    call_data.tts_characters_count = summary.tts_characters_count
    call_data.stt_audio_duration = summary.stt_audio_duration
    call_data.tts_audio_duration = summary.tts_audio_duration
    c_metrics_v2 = call_data.consolidate_metrics_v2(metrics_batch)
    call_data.details = str(c_metrics_v2)
    call_data.ttft = c_metrics_v2.get("ttft")
    call_data.ttfb = c_metrics_v2.get("sum_ttfb")
    call_data.average_ttft = c_metrics_v2.get("average_ttft")
    call_data.average_ttfb = c_metrics_v2.get("average_ttfb")
    call_data.tts_duration = c_metrics_v2.get("sum_tts_duration")
    call_data.stt_duration = c_metrics_v2.get("sum_stt_duration")
    call_data.llm_duration = c_metrics_v2.get("sum_llm_duration")
    call_data.end_of_utterance_delay = c_metrics_v2.get("sum_end_of_utterance_delay")

    if LOG_METRICS_VERBOSE:
        logger.info(f" Consolidated metrics summary:\n{pprint.pformat(c_metrics_v2)}")
    metrics_output_dir = os.getenv("METRICS_LOG_PATH", "metrics_output") # Configurable directory

    job_id = ctx_obj.get("job_id", call_data.room_id if call_data.room_id else "unknown_job")

    try:
        os.makedirs(metrics_output_dir, exist_ok=True) # Ensure directory exists

        # Create a unique filename
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        # Use a combination of job_id (or room_id) and timestamp for uniqueness
        filename_safe_job_id = "".join(c if c.isalnum() else "_" for c in str(job_id)) # Sanitize job_id for filename
        metrics_filename = os.path.join(metrics_output_dir, f"callmetrics_{filename_safe_job_id}_{timestamp_str}.json")

        metrics_payload = {
            "job_id": str(job_id), # Ensure job_id is a string
            "agent_id": str(call_data.agent_id) if call_data.agent_id else "unknown_agent",
            "description": ctx_obj["agent_name"],
            "room_id": str(call_data.room_id) if call_data.room_id else "unknown_room",
            "call_status": str(call_data.status),
            "call_start_time_iso": call_data.start_time.isoformat() if call_data.start_time else None,
            "call_end_time_iso": call_data.end_time.isoformat() if call_data.end_time else None,
            "call_duration_seconds": call_data.duration_seconds,
            "llm_prompt_tokens": call_data.llm_prompt_tokens,
            "llm_completion_tokens": call_data.llm_completion_tokens,
            "tts_characters_count": call_data.tts_characters_count,
            "stt_audio_duration": call_data.stt_audio_duration,
            "tts_audio_duration": call_data.tts_audio_duration,
            "ttft": call_data.ttft,
            "ttfb": call_data.ttfb,
            "average_ttft": call_data.average_ttft,
            "average_ttfb": call_data.average_ttfb,
            "tts_duration": call_data.tts_duration,
            "stt_duration": call_data.stt_duration,
            "llm_duration": call_data.llm_duration,
            "end_of_utterance_delay": call_data.end_of_utterance_delay,
            "details": call_data.details,
            "skills": skills,
            "metrics_batch": metrics_batch
        }

        with open(metrics_filename, 'w') as f:
            json.dump(metrics_payload, f, indent=2, default=str) # Use default=str to handle datetime objects

        if LOG_METRICS_VERBOSE:
            logger.info(f" Metrics saved to {metrics_filename}")

    except Exception as e:
        logger.error(f" Error saving metrics to file: {e}", exc_info=True)

    # Send metrics to API
    try:
        if fast_api_client:
            serialized_payload = serialize_payload_events(metrics_payload)
            response = await fast_api_client.post_call_data(serialized_payload)
            if LOG_METRICS_VERBOSE:
                logger.info(f" API response: {response}")
        else:
            logger.warning(" No fast_api_client available for sending metrics.")
    except Exception as e:
        logger.error(f" Error sending metrics to API: {e}", exc_info=True)
