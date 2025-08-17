import requests
import os
from datetime import datetime
from typing import Dict, List, Optional, Tuple

class WeatherService:
    """Weather service for getting 5-day forecasts using OpenWeatherMap API"""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or 'fd94c86864c1809c326f7f0b6add6acc'
        self.base_url = "http://api.openweathermap.org/data/2.5/forecast"
        self.geocoding_url = "http://api.openweathermap.org/geo/1.0/zip"
    
    def get_coordinates_from_postcode(self, postcode: str, country_code: str = "GB") -> Optional[Tuple[float, float]]:
        """Get latitude and longitude from postcode"""
        try:
            # For UK postcodes, use smarter extraction
            if country_code == "GB":
                # First try the full postcode without spaces
                clean_postcode = postcode.replace(" ", "").upper()
                url = f"{self.geocoding_url}?zip={clean_postcode},{country_code}&appid={self.api_key}"
                response = requests.get(url, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    return data['lat'], data['lon']
                
                # If full postcode fails, extract area code
                # For UK postcodes with space (SW6 2GX), take the part before space
                if ' ' in postcode:
                    area_code = postcode.split(' ')[0].upper()
                else:
                    # For postcodes without space, use regex to extract area
                    import re
                    area_match = re.match(r'^([A-Z]{1,2}[0-9][A-Z]?)', clean_postcode)
                    if area_match:
                        area_code = area_match.group(1)
                    else:
                        return None
                
                # Try the area code
                url = f"{self.geocoding_url}?zip={area_code},{country_code}&appid={self.api_key}"
                response = requests.get(url, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    return data['lat'], data['lon']
                    
            else:
                # For non-UK postcodes, use as-is
                clean_postcode = postcode.replace(" ", "").upper()
                url = f"{self.geocoding_url}?zip={clean_postcode},{country_code}&appid={self.api_key}"
                response = requests.get(url, timeout=10)
                response.raise_for_status()
                
                data = response.json()
                return data['lat'], data['lon']
                
            return None
            
        except Exception as e:
            return None
    
    def get_weather_forecast(self, postcode: str, country_code: str = "GB") -> Optional[Dict]:
        """Get 5-day weather forecast for a postcode"""
        try:
            # Get coordinates from postcode
            coords = self.get_coordinates_from_postcode(postcode, country_code)
            if not coords:
                return {"error": "Invalid postcode or unable to get location"}
            
            lat, lon = coords
            
            # Get weather forecast
            url = f"{self.base_url}?lat={lat}&lon={lon}&appid={self.api_key}&units=metric"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            return self._process_forecast_data(data, postcode)
            
        except requests.exceptions.RequestException as e:
            return {"error": f"Network error: {str(e)}"}
        except Exception as e:
            return {"error": f"Error getting weather forecast: {str(e)}"}
    
    def _process_forecast_data(self, data: Dict, postcode: str) -> Dict:
        """Process raw API data into formatted forecast"""
        try:
            location = data.get('city', {})
            forecasts = data.get('list', [])
            
            # Group forecasts by day
            daily_forecasts = {}
            
            for forecast in forecasts:
                dt = datetime.fromtimestamp(forecast['dt'])
                date_key = dt.strftime('%Y-%m-%d')
                
                # Extract weather data
                weather_data = {
                    'time': dt.strftime('%H:%M'),
                    'timestamp': forecast['dt'],
                    'temperature': round(forecast['main']['temp']),
                    'feels_like': round(forecast['main']['feels_like']),
                    'humidity': forecast['main']['humidity'],
                    'description': forecast['weather'][0]['description'].title(),
                    'icon': forecast['weather'][0]['icon'],
                    'wind_speed': round(forecast['wind']['speed'] * 3.6, 1),  # Convert m/s to km/h
                    'wind_direction': forecast['wind'].get('deg', 0),
                    'precipitation': forecast.get('rain', {}).get('3h', 0) + forecast.get('snow', {}).get('3h', 0),
                    'visibility': forecast.get('visibility', 10000) / 1000  # Convert to km
                }
                
                if date_key not in daily_forecasts:
                    daily_forecasts[date_key] = {
                        'date': dt.strftime('%A, %B %d'),
                        'date_short': dt.strftime('%a %d'),
                        'forecasts': [],
                        'min_temp': weather_data['temperature'],
                        'max_temp': weather_data['temperature'],
                        'tennis_conditions': 'Unknown'
                    }
                
                daily_forecasts[date_key]['forecasts'].append(weather_data)
                daily_forecasts[date_key]['min_temp'] = min(daily_forecasts[date_key]['min_temp'], weather_data['temperature'])
                daily_forecasts[date_key]['max_temp'] = max(daily_forecasts[date_key]['max_temp'], weather_data['temperature'])
            
            # Assess tennis playing conditions for each day
            for day_data in daily_forecasts.values():
                try:
                    tennis_assessment = self._assess_tennis_conditions(day_data['forecasts'])
                    
                    # Set defaults in case of missing keys
                    day_data['tennis_conditions'] = tennis_assessment.get('rating', 'Unknown')
                    day_data['tennis_details'] = tennis_assessment.get('details', 'Weather data unavailable')
                    day_data['tennis_stats'] = {
                        'temperature_range': tennis_assessment.get('temperature_range', f"{day_data['min_temp']}°C - {day_data['max_temp']}°C"),
                        'max_wind': tennis_assessment.get('max_wind', 'Unknown'),
                        'precipitation': tennis_assessment.get('precipitation', '0.0mm'),
                        'avg_humidity': tennis_assessment.get('avg_humidity', 'Unknown')
                    }
                except Exception as e:
                    # Fallback if tennis assessment fails
                    day_data['tennis_conditions'] = 'Unknown'
                    day_data['tennis_details'] = 'Weather assessment unavailable'
                    day_data['tennis_stats'] = {
                        'temperature_range': f"{day_data['min_temp']}°C - {day_data['max_temp']}°C",
                        'max_wind': 'Unknown',
                        'precipitation': '0.0mm',
                        'avg_humidity': 'Unknown'
                    }
            
            # Sort by date and take first 5 days
            sorted_days = sorted(daily_forecasts.items())[:5]
            
            return {
                'location': {
                    'name': location.get('name', 'Unknown'),
                    'country': location.get('country', ''),
                    'postcode': postcode
                },
                'daily_forecasts': dict(sorted_days),
                'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
        except Exception as e:
            return {"error": f"Error processing forecast data: {str(e)}"}
    
    def _assess_tennis_conditions(self, forecasts: List[Dict]) -> Dict[str, str]:
        """Assess tennis playing conditions based on weather data"""
        # Find best conditions during daylight hours (7 AM - 8 PM for tennis)
        daylight_forecasts = [f for f in forecasts if 7 <= int(f['time'].split(':')[0]) <= 20]
        
        if not daylight_forecasts:
            return {
                'rating': 'Unknown', 
                'details': 'No daylight hours data available',
                'temperature_range': 'Unknown',
                'max_wind': 'Unknown',
                'precipitation': '0.0mm',
                'avg_humidity': 'Unknown'
            }
        
        # Check various factors with error handling
        try:
            avg_temp = sum(f['temperature'] for f in daylight_forecasts) / len(daylight_forecasts)
            max_wind = max(f['wind_speed'] for f in daylight_forecasts)
            total_precipitation = sum(f['precipitation'] for f in daylight_forecasts)
            avg_humidity = sum(f['humidity'] for f in daylight_forecasts) / len(daylight_forecasts)
            min_temp = min(f['temperature'] for f in daylight_forecasts)
            max_temp = max(f['temperature'] for f in daylight_forecasts)
        except (KeyError, ValueError, ZeroDivisionError) as e:
            # Return default values if calculation fails
            return {
                'rating': 'Unknown', 
                'details': f'Error calculating weather conditions: {str(e)}',
                'temperature_range': 'Unknown',
                'max_wind': 'Unknown',
                'precipitation': '0.0mm',
                'avg_humidity': 'Unknown'
            }
        
        # Tennis-specific condition assessment
        issues = []
        
        # Temperature assessment
        if avg_temp < 8:
            issues.append("Too cold for comfortable play")
        elif avg_temp > 32:
            issues.append("Very hot - frequent breaks needed")
        elif avg_temp > 28:
            issues.append("Warm - ensure hydration")
        
        # Wind assessment - critical for tennis
        if max_wind > 30:
            issues.append("Very windy - ball control difficult")
        elif max_wind > 20:
            issues.append("Windy - affects ball trajectory")
        elif max_wind > 12:
            issues.append("Breezy conditions")
        
        # Precipitation assessment
        if total_precipitation > 10:
            issues.append("Heavy rain expected - courts likely unplayable")
        elif total_precipitation > 3:
            issues.append("Rain expected - wet courts possible")
        elif total_precipitation > 0.5:
            issues.append("Light rain possible")
        
        # Humidity assessment
        if avg_humidity > 85:
            issues.append("Very humid - slower court conditions")
        elif avg_humidity > 75:
            issues.append("Humid conditions")
        
        # Overall rating
        if total_precipitation > 10 or max_wind > 30 or avg_temp < 5 or avg_temp > 35:
            rating = 'Poor'
            summary = "Not recommended for tennis"
        elif total_precipitation > 3 or max_wind > 20 or avg_temp < 8 or avg_temp > 32:
            rating = 'Fair'
            summary = "Playable but challenging conditions"
        elif total_precipitation > 0.5 or max_wind > 12 or avg_temp < 12 or avg_temp > 28:
            rating = 'Good'
            summary = "Good for tennis with minor considerations"
        else:
            rating = 'Excellent'
            summary = "Perfect tennis weather"
        
        # Create detailed assessment
        if not issues:
            details = summary
        else:
            details = f"{summary}. {', '.join(issues)}"
        
        return {
            'rating': rating,
            'details': details,
            'temperature_range': f"{min_temp}°C - {max_temp}°C",
            'max_wind': f"{max_wind} km/h",
            'precipitation': f"{total_precipitation:.1f}mm",
            'avg_humidity': f"{avg_humidity:.0f}%"
        }
    
    def get_current_weather(self, postcode: str, country_code: str = "GB") -> Optional[Dict]:
        """Get current weather for a postcode"""
        try:
            coords = self.get_coordinates_from_postcode(postcode, country_code)
            if not coords:
                return {"error": "Invalid postcode or unable to get location"}
            
            lat, lon = coords
            
            url = f"http://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={self.api_key}&units=metric"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            return {
                'temperature': round(data['main']['temp']),
                'feels_like': round(data['main']['feels_like']),
                'description': data['weather'][0]['description'].title(),
                'icon': data['weather'][0]['icon'],
                'humidity': data['main']['humidity'],
                'wind_speed': round(data['wind']['speed'] * 3.6, 1),
                'visibility': data.get('visibility', 10000) / 1000
            }
            
        except Exception as e:
            return {"error": f"Error getting current weather: {str(e)}"}