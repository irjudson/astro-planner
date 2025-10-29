# Quick Start Guide

Get Astro Planner running in 5 minutes!

## Prerequisites

- Python 3.11+ installed
- Git (if cloning from repository)
- Internet connection (for weather data)

## Installation

### Method 1: Automated Setup (Recommended)

1. **Navigate to the project directory**
   ```bash
   cd astro-planner
   ```

2. **Run the setup script**
   ```bash
   ./setup.sh
   ```

   This script will:
   - Check your Python version
   - Create a virtual environment
   - Install all dependencies
   - Create a `.env` configuration file

3. **Activate the virtual environment**
   ```bash
   source venv/bin/activate
   ```

4. **Start the server**
   ```bash
   cd backend
   python -m uvicorn app.main:app --reload
   ```

5. **Open your browser**
   Navigate to: http://localhost:8000

### Method 2: Docker (Alternative)

If you prefer Docker:

```bash
cd astro-planner
docker-compose up -d
```

Then open http://localhost:8000

## First Use

1. **Review Default Settings**
   - Location: Three Forks, MT (45.9183°N, 111.5433°W)
   - Date: Today (plans for tonight's astronomical night)
   - Object types: All selected
   - Altitude range: 30-80°

2. **Customize (Optional)**
   - Update location to your observing site
   - Adjust date if planning for a future session
   - Modify altitude constraints if needed

3. **Generate Plan**
   - Click "Generate Observing Plan"
   - Wait 5-10 seconds for calculations
   - Review scheduled targets

4. **Export Your Plan**
   - Choose an export format:
     - **Seestar Plan Mode**: For direct import to Seestar S50
     - **Text**: Human-readable schedule
     - **CSV**: For analysis in Excel/Sheets

## Adding Weather Data (Optional)

For better target selection, add a free OpenWeatherMap API key:

1. **Get API Key**
   - Visit https://openweathermap.org/api
   - Sign up for free account
   - Copy your API key

2. **Configure**
   ```bash
   # Edit backend/.env
   nano backend/.env  # or use your preferred editor

   # Add your key:
   OPENWEATHERMAP_API_KEY=your_key_here
   ```

3. **Restart the server**
   ```bash
   # Press Ctrl+C to stop
   python -m uvicorn app.main:app --reload
   ```

## Verify Installation

Run the test suite:

```bash
# Make sure server is running in another terminal
python test_api.py
```

You should see all tests pass.

## Common Issues

### "Python version too old"
- Install Python 3.11 or higher
- On Ubuntu/Debian: `sudo apt install python3.11`
- On macOS with Homebrew: `brew install python@3.11`

### "Port 8000 already in use"
- Stop other services using port 8000
- Or change port: `uvicorn app.main:app --port 8001`

### "Module not found"
- Make sure virtual environment is activated
- Reinstall dependencies: `pip install -r backend/requirements.txt`

### Frontend not loading
- Check that you're accessing http://localhost:8000 (not /api/docs)
- Clear browser cache
- Check browser console for errors

## Next Steps

- Read [USAGE.md](USAGE.md) for detailed usage examples
- Explore [ARCHITECTURE.md](ARCHITECTURE.md) for technical details
- Customize the DSO catalog in `backend/app/services/catalog_service.py`
- Adjust scheduling parameters in `backend/.env`

## Quick Tips

1. **Plan Tonight**: Just click "Generate" with default settings
2. **Different Location**: Update lat/lon and timezone before generating
3. **Future Date**: Change the date picker to plan ahead
4. **Filter Objects**: Uncheck object types you don't want
5. **Higher in Sky**: Increase min altitude to 35-40° for better seeing

## Getting Help

- Check the full README.md for detailed information
- Review API documentation at http://localhost:8000/api/docs
- Run `test_api.py` to diagnose issues

---

Happy planning! 🔭✨
