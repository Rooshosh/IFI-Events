from datetime import datetime
from flask import Blueprint, render_template, request, make_response, current_app
from icalendar import Calendar, Event as ICalEvent
from web.api import EventAPIClient

# Create the blueprint
events_bp = Blueprint('events', __name__)

def get_events():
    """Fetch events from the API"""
    try:
        client = EventAPIClient(
            base_url=current_app.config['API_BASE_URL'],
            timeout=current_app.config['API_TIMEOUT']
        )
        return client.get_events()
    except Exception as e:
        current_app.logger.error(f"Error fetching events from API: {e}")
        return []

@events_bp.route('/')
def index():
    """Render the events page."""
    events = get_events()
    return render_template('index.html', events=events)

@events_bp.route('/calendar.ics')
def ics_feed():
    """Generate an iCalendar feed of all events."""
    events = get_events()
    
    # Create calendar
    cal = Calendar()
    cal.add('prodid', '-//IFI Events//ifievents.no//')
    cal.add('version', '2.0')
    cal.add('x-wr-calname', 'IFI Events')
    cal.add('x-wr-timezone', 'Europe/Oslo')
    
    # Add events to calendar
    for event in events:
        cal_event = ICalEvent()
        cal_event.add('summary', event.title)
        cal_event.add('dtstart', event.start_time)
        
        if event.end_time:
            cal_event.add('dtend', event.end_time)
            
        if event.description:
            cal_event.add('description', event.description)
            
        if event.location:
            cal_event.add('location', event.location)
            
        if event.source_url:
            cal_event.add('url', event.source_url)
            
        cal.add_component(cal_event)
    
    # Generate response
    response = make_response(cal.to_ical())
    response.headers['Content-Type'] = 'text/calendar; charset=utf-8'
    response.headers['Content-Disposition'] = 'attachment; filename=calendar.ics'
    
    return response

@events_bp.route('/test-500')
def test_500():
    """Route to test 500 error page"""
    # Deliberately raise an exception
    raise Exception("This is a test error to view the 500 error page") 