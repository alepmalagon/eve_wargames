# EVE Wargames Setup Guide

This guide will help you set up the EVE Wargames application for development and production.

## Prerequisites

- Docker and Docker Compose
- Node.js 18+ (for local frontend development)
- Python 3.11+ (for local backend development)
- PostgreSQL 15+ (if running without Docker)
- Redis 7+ (if running without Docker)

## Quick Start with Docker

1. **Clone the repository**
   ```bash
   git clone https://github.com/alepmalagon/eve_wargames.git
   cd eve_wargames
   ```

2. **Set up environment variables**
   ```bash
   cp .env.example .env
   ```
   
   Edit `.env` and configure the following required variables:
   - `SECRET_KEY`: Generate a secure secret key
   - `ESI_CLIENT_ID`: Your EVE Online ESI application client ID
   - `ESI_CLIENT_SECRET`: Your EVE Online ESI application client secret

3. **Start the application**
   ```bash
   docker-compose up -d
   ```

4. **Access the application**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs

## ESI API Setup

To use the EVE Online ESI API, you need to create an application:

1. Go to https://developers.eveonline.com/
2. Create a new application
3. Set the callback URL to `http://localhost:8000/auth/callback` (for development)
4. Note down your Client ID and Client Secret
5. Add these to your `.env` file

### Required ESI Scopes

The application uses the following ESI scopes:
- No authentication required for faction warfare data (public endpoints)

## Local Development

### Backend Development

1. **Set up Python environment**
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Set up database**
   ```bash
   # Start PostgreSQL and Redis with Docker
   docker-compose up -d postgres redis
   
   # Run database migrations
   python -c "from app.database import init_db; init_db()"
   ```

3. **Start the backend server**
   ```bash
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

### Frontend Development

1. **Set up Node.js environment**
   ```bash
   cd frontend
   npm install
   ```

2. **Start the development server**
   ```bash
   npm run dev
   ```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DEBUG` | Enable debug mode | `false` |
| `SECRET_KEY` | Secret key for JWT tokens | Required |
| `DATABASE_URL` | PostgreSQL connection URL | `postgresql://eve_user:eve_password@localhost:5432/eve_wargames` |
| `REDIS_URL` | Redis connection URL | `redis://localhost:6379/0` |
| `ESI_CLIENT_ID` | ESI application client ID | Required |
| `ESI_CLIENT_SECRET` | ESI application client secret | Required |
| `DATA_COLLECTION_INTERVAL` | Data collection interval (seconds) | `300` |

### Database Schema

The application automatically creates the following tables:
- `factions`: Faction information
- `systems`: System information and current status
- `system_snapshots`: Historical system control data
- `kills`: Individual killmail data
- `kill_statistics`: Aggregated kill statistics
- `faction_warfare_snapshots`: Warzone-wide statistics

## Data Collection

The application includes background tasks for collecting data from the ESI API:

1. **System Control Data**: Collected every 5 minutes
2. **Kill Data**: Collected every 15 minutes (when available)
3. **Faction Warfare Statistics**: Collected every 10 minutes

### Starting Background Workers

```bash
# Start Celery worker
celery -A app.tasks.scheduler worker --loglevel=info

# Start Celery beat scheduler
celery -A app.tasks.scheduler beat --loglevel=info
```

## Production Deployment

### Docker Production Setup

1. **Create production environment file**
   ```bash
   cp .env.example .env.production
   ```
   
   Update with production values:
   - Set `DEBUG=false`
   - Use strong `SECRET_KEY`
   - Configure production database URLs
   - Set proper CORS origins

2. **Build and deploy**
   ```bash
   docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
   ```

### Security Considerations

- Use strong, unique secret keys
- Enable HTTPS in production
- Restrict CORS origins to your domain
- Use environment-specific database credentials
- Enable database SSL connections
- Set up proper firewall rules

## Monitoring

### Health Checks

- Backend health: `GET /health`
- Database connectivity: Automatic health checks in Docker Compose
- Redis connectivity: Automatic health checks in Docker Compose

### Logging

- Application logs: Structured logging with configurable levels
- Access logs: Uvicorn access logs
- Error tracking: Console and file logging

## Troubleshooting

### Common Issues

1. **Database connection errors**
   - Ensure PostgreSQL is running
   - Check database credentials in `.env`
   - Verify database exists

2. **ESI API errors**
   - Check ESI client credentials
   - Verify ESI service status
   - Check rate limiting

3. **Frontend build errors**
   - Clear node_modules and reinstall
   - Check Node.js version compatibility
   - Verify environment variables

### Debug Mode

Enable debug mode for detailed error information:
```bash
export DEBUG=true
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## Support

For issues and questions:
- Check the GitHub issues
- Review the API documentation at `/docs`
- Check EVE Online ESI documentation
