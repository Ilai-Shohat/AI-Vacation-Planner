from serpapi import GoogleSearch
from openai import OpenAI
import unicodedata
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import re

OPENAI_KEY = 'sk-proj-eurY5CPWg333LbgyXj54T3BlbkFJQAvXrbGfYwcBMA0cKw2v'
SERPAPI_KEY = '5c9ba309151f872e593963687eeb20cc554d43f103c203369003144f1ea43699'
OPENAI_CLIENT = OpenAI(api_key=OPENAI_KEY)

def request_prompt(prompt) -> str:
    completion = OPENAI_CLIENT.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are a travel assistant."},
            {"role": "user", "content": prompt}
        ]
    )
    response = completion.choices[0].message.content
    if response is None:
        return ''
    else:
        return response


def findTopDestinations(start_month: int, end_month: int, trip_type: str):
    good_dest = []

    prompt = f"""
    Suggest 7 possible destinations for a {trip_type} vacation that are compatible from the start month: {start_month} to end month: {end_month}. generate a list of the top destinations in the given time of the year, and provide their airport codes.\n
    Do not include any other information in your response.
    The format should be:
    <destination>,<airport_code>
    <destination>,<airport_code>
    <destination>,<airport_code>
    <destination>,<airport_code>
    <destination>,<airport_code>
    <destination>,<airport_code>
    <destination>,<airport_code>
    Where <destination> is the name of the destination and <airport_code> is the airport code of the destination.
    Make sure to exclude any commas in the destination or airport_code.
    Try to suggest nearest city with an airport that are well-known and have international airports.
    """

    response = request_prompt(prompt).split("\n")[:7]
    for destination in response:
        destination_name, airport_code = destination.split(",")
        good_dest.append((destination_name.strip(), airport_code.strip()))

    return good_dest


def generate_daily_plan(arrival_date_and_time: str, departure_date_and_time: str, trip_type: str, destination: str) -> str:

    prompt = f"""
    Create a daily plan for a {trip_type} vacation to {destination}. My arrival date and time: {arrival_date_and_time}, my departure date and time: {departure_date_and_time}.
    Please generate a daily plan for this vacation in the given time and location.
    Each day should include at least 3 activities, and at most 4 activities.
    In addition, please pick the 4 most exciting activities from all the activities you provided for the entire vacation.
    Do not include any other information in your response.
    The format should be:
    Day 1:
    <activity>
    <activity>
    Day 2:
    <activity>
    <activity>
    Day 3:
    <activity>
    <activity>
    Day N:
    <activity>
    <activity>
    4 Best Moments:
    <moment>
    <moment>
    <moment>
    <moment>

    Here are some guidance:
    N is the number of days in the trip.
    <activity> is 1 of the 3-4 activities at the current day, and <moment> 1 of the most exciting activities.
    make sure to provide 3-4 activities for each day and exactly 4 best moments.
    Do not make the list with bullets or dashes.

    Some considerations:
    Take into consideration the time of the day when the arrival and departure are.
    Make sure to include a variety of activities that cater to different interests and preferences.
    """

    response = request_prompt(prompt)
    return response

def findCheapestFlights(destinations: list, start_date: str, end_date: str, budget: int) -> dict:
    flights = {}
    for destination in destinations:

        destination_name = destination[0]
        destination_airport_code = destination[1]
        if destination_airport_code == '':
            print(f"Could not find airport code for {destination_name}")
            continue
        from_TLV_flight_search_params = {
            "engine": "google_flights",
            "departure_id": "TLV",
            "arrival_id": destination_airport_code,
            "outbound_date": start_date,
            "currency": "USD",
            "hl": "en",
            "api_key": SERPAPI_KEY,
            "type": "2"
        }
        flight_search = GoogleSearch(from_TLV_flight_search_params)
        results = flight_search.get_dict()

        if 'error' in results.keys():
            print(
                f"Error from serpapi: from TLV to {destination[1]}")
            continue
        elif 'best_flights' in results.keys():
            from_TLV_cheapest_flight = results['best_flights'][0]
        else:
            from_TLV_cheapest_flight = results['other_flights'][0]

        to_TLV_flight_search_params = {
            "engine": "google_flights",
            "departure_id": destination_airport_code,
            "arrival_id": "TLV",
            "outbound_date": end_date,
            "currency": "USD",
            "hl": "en",
            "api_key": SERPAPI_KEY,
            "type": "2",
        }
        flight_search = GoogleSearch(to_TLV_flight_search_params)
        results = flight_search.get_dict()

        if 'error' in results.keys():
            print(
                f"Error from serpapi: from {destination[0]} {destination[1]} to TLV")
            continue

        elif 'best_flights' in results.keys():
            to_TLV_cheapest_flight = results['best_flights'][0]
        else:
            to_TLV_cheapest_flight = results['other_flights'][0]

        total_flights_price = from_TLV_cheapest_flight['price'] + to_TLV_cheapest_flight['price']
        if total_flights_price > budget:
            print(
                f"Total price of flights to {destination_name} and back is above budget")
            continue

        flights[unicodedata.normalize('NFKD', destination[0]).encode('ascii', 'ignore').decode('utf-8')] = [[from_TLV_cheapest_flight, to_TLV_cheapest_flight], budget - total_flights_price]

    return flights


def findHotels(destinations: dict, start_date: str, end_date: str) -> dict:
    hotels = {}
    for key, destination in destinations.items():
        destination_name = key
        hotel_search_params = {
            "engine": "google_hotels",
            "q": f"Hotels in {destination_name}",
            "check_in_date": start_date,
            "check_out_date": end_date,
            "adults": "1",
            "currency": "USD",
            "hl": "en",
            "api_key": SERPAPI_KEY
        }

        hotel_search = GoogleSearch(hotel_search_params)
        results = hotel_search.get_dict()
        if 'error' in results.keys():
            hotels[key] = None
        else:
            hotels[key] = [results['properties'], destination[1]]  
    return hotels


def findMostExpensiveHotelsInBudget(hotels: dict) -> dict:
    max_hotel = {}
    for key, hotels_and_leftover_budget in hotels.items():
        max_price = 0
        if hotels_and_leftover_budget is None:
            continue
        for hotel in hotels_and_leftover_budget[0]:
            if 'total_rate' not in hotel.keys():
                continue
            hotel_price = hotel['total_rate']['extracted_lowest']
            if hotel_price > max_price and hotels_and_leftover_budget[1] >= hotel_price:  
                max_price = hotel_price
                max_hotel[key] = hotel

    return max_hotel


def generate_dalle_image(activity: str, destination: str) -> str:
    prompt = f"""Subject: Create an image showing {activity} in {destination}.      
            Style: make the image as real as possible"""

    response = OPENAI_CLIENT.images.generate(
        model="dall-e-3",
        prompt=prompt,
        size="1024x1024",
        quality="standard",
        n=1,
    )

    url = response.data[0].url
    if url:
        return url
    else:
        return ''


def retrieve_top_options(start_date, end_date, trip_type, budget):
    # get the top 7 destinations
    destinations = findTopDestinations(int(start_date.split("-")[1]), int(end_date.split("-")[1]), trip_type)
    # search for flights
    flights: dict = findCheapestFlights(destinations, start_date, end_date, budget)
    # search for hotels
    hotels: dict = findHotels(flights, start_date, end_date)
    # get the most expensive hotels
    most_expensive_hotels: dict = findMostExpensiveHotelsInBudget(hotels)

    data: dict = {key: {} for key in most_expensive_hotels.keys()}

    for key in data.keys():

        # destination details
        data[key]['destination'] = str(key.split('@')[0])

        # flights details
        data[key]['arrival_daytime'] = str(flights[key][0][0]['flights'][len(flights[key][0][0]['flights']) - 1]['arrival_airport']['time'])
        data[key]['arrival_total_price'] = float(flights[key][0][0]['price']) 
        data[key]['arrival_connections_number'] = str(len(flights[key][0][0]['flights']) - 1) 
        data[key]['arrival_connections_list'] = [str(unicodedata.normalize('NFKD', flight['arrival_airport']['name']).encode('ascii', 'ignore').decode('utf-8')) for flight in flights[key][0][0]['flights'][:-1]]  
        data[key]['departure_daytime'] = str(flights[key][0][1]['flights'][0]['departure_airport']['time'])  
        data[key]['departure_total_price'] = float(flights[key][0][1]['price'])  
        data[key]['departure_connections_number'] = str(len(flights[key][0][1]['flights']) - 1)  
        data[key]['departure_connections_list'] = [str(unicodedata.normalize('NFKD', flight['departure_airport']['name']).encode('ascii', 'ignore').decode('utf-8')) for flight in flights[key][0][1]['flights'][1:]]  
        data[key]['flights_total_price'] = float(data[key]['arrival_total_price'] + data[key]['departure_total_price'])  

        # hotels details
        data[key]['hotel_name'] = str(unicodedata.normalize('NFKD', most_expensive_hotels[key]['name']).encode('ascii', 'ignore').decode('utf-8'))
        data[key]['hotel_total_price'] = float(most_expensive_hotels[key]['total_rate']['extracted_lowest'])  

    print(data)
    return {k: data[k] for i, k in enumerate(data) if i < 5}

def getPlanAndImages(arrival_date: str, departure_date: str, trip_type: str, destination: str):
    # get the daily plan
    daily_plan = generate_daily_plan(arrival_date, departure_date, trip_type, destination)  
    print(daily_plan)
    activities = daily_plan.splitlines()[-4:]
    images = []
    for activity in activities:
        image_url = generate_dalle_image(activity, destination)
        images.append(image_url)

    # go over the daily_plan and create a dictionary with the days and activities for each day, without the 4 best moments
    daily_plan_dict = {}
    for line in daily_plan.splitlines()[:-5]:
        if re.match(r"^Day \d+:", line):
            # take the day number
            day_number = int(line.split(" ")[1].split(":")[0])
            daily_plan_dict[day_number] = []
        elif line.strip() != "":
            daily_plan_dict[day_number].append(line)

    return {"daily_plan": daily_plan_dict, "images": images}

# FastAPI setup
app = FastAPI()
# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    # Allows all methods, including GET, POST, PUT, DELETE, etc.
    allow_methods=["*"],
    allow_headers=["*"],  # Allows all headers
)

# FastAPI routes
@app.get("/top-5-options")
def fetch_top_5_options(start_date: str, end_date: str, trip_type: str, budget: int):
    try:
        return retrieve_top_options(start_date, end_date, trip_type, budget)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/daily-plan-and-images")
def get_daily_plan_and_images(arrival_date: str, departure_date: str, trip_type: str, destination: str):
    try:
        return getPlanAndImages(arrival_date, departure_date, trip_type, destination)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))