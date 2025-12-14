# EVE Wargames

A comprehensive web application for tracking and analyzing EVE Online Faction Warfare data, specifically focused on the Minmatar/Amarr warzone.

## Features

- **Real-time System Control Tracking**: Monitor capture percentages and advantage percentages for all systems in the Minmatar/Amarr warzone
- **Kill Statistics**: Track kills per faction, corporation, and alliance with detailed breakdowns by system
- **Historical Trends**: Analyze trends over time for all metrics
- **Warzone Analytics**: Comprehensive warzone-wide statistics and projections
- **Interactive Dashboards**: Modern, responsive web interface with real-time data visualization
- **Wargame Simulation**: Simulate scenarios based on current or custom data

## Technology Stack

### Backend
- **FastAPI**: Modern, fast web framework for building APIs
- **SQLAlchemy**: SQL toolkit and ORM for database operations
- **PostgreSQL**: Primary database with TimescaleDB for time-series data
- **Redis**: Caching layer for API responses
- **Celery**: Background task processing for data collection

### Frontend
- **React**: Modern UI library with TypeScript
- **Vite**: Fast build tool and development server
- **Chart.js/Recharts**: Data visualization libraries
- **Axios**: HTTP client for API communication
- **Tailwind CSS**: Utility-first CSS framework

### Data Source
- **EVE Online ESI API**: Official EVE Online API for real-time game data

## Project Structure

```
eve_wargames/
├── backend/                 # FastAPI backend application
│   ├── app/
│   │   ├── api/            # API endpoints
│   │   ├── models/         # Database models
│   │   ├── services/       # Business logic and external services
│   │   ├── schemas/        # Pydantic models for request/response
│   │   └── tasks/          # Background tasks
│   ├── requirements.txt    # Python dependencies
│   └── Dockerfile         # Backend container configuration
├── frontend/               # React frontend application
│   ├── src/
│   │   ├── components/     # React components
│   │   ├── services/       # API client and utilities
│   │   └── types/          # TypeScript type definitions
│   ├── package.json       # Node.js dependencies
│   └── Dockerfile         # Frontend container configuration
├── docs/                   # Documentation
├── docker-compose.yml      # Development environment setup
└── README.md              # This file
```

## Quick Start

### Prerequisites
- Docker and Docker Compose
- Node.js 18+ (for local frontend development)
- Python 3.11+ (for local backend development)

### Development Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/alepmalagon/eve_wargames.git
   cd eve_wargames
   ```

2. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Start the development environment**
   ```bash
   docker-compose -f docker-compose.dev.yml up
   ```

4. **Access the application**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs

## ESI API Setup

To use the EVE Online ESI API, you'll need to:

1. Create an application at https://developers.eveonline.com/
2. Configure the appropriate scopes for faction warfare data
3. Add your client ID and secret to the environment variables

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Disclaimer

This application is not affiliated with or endorsed by CCP Games or EVE Online. EVE Online is a trademark of CCP hf.
