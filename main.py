import json
from serpapi import GoogleSearch
from openai import OpenAI
import unicodedata
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import re

SERPAPI_KEY = '2303fe23b12fb5df4cfa6944849d14dd7a9b472ea6e28ee100c0ff0e99f9ed7d'
OPENAI_CLIENT = OpenAI(api_key="sk-proj-5hGNQsFq3ncGG0V3vcOeT3BlbkFJej39qWF8lI2qLnJqTOjt")  # nopep8


def get_normal_name_without_foreign_chars(str: str) -> str:
    return unicodedata.normalize('NFKD', str).encode('ascii', 'ignore').decode('utf-8')  # nopep8


def upload_file_to_open_ai(file_path: str) -> str:
    response = OPENAI_CLIENT.files.create(file=open(file_path, 'rb'), purpose='assistants')  # nopep8
    return response.id


def send_prompt(prompt) -> str:
    completion = OPENAI_CLIENT.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are an experienced worldwide vacation planner. Additionally you are familiar with airports around the world."},
            {"role": "user", "content": prompt}
        ]
    )
    response = completion.choices[0].message.content
    if response is None:
        return ''
    else:
        return response


def get_top_destinations(start_month: int, end_month: int, trip_type: str):

    final_list = []
    months = {
        1: "January",
        2: "February",
        3: "March",
        4: "April",
        5: "May",
        6: "June",
        7: "July",
        8: "August",
        9: "September",
        10: "October",
        11: "November",
        12: "December"
    }

    prompt = f"""
    Given the start month {months[start_month]} and end month {months[end_month]}, generate a list of the top 10 destinations for a {trip_type} vacation in the given time of the year.\n
    Do not include any other information in your response.
    The format should be:
    <destination>,<nearest_city_with_airport>,<country>
    <destination>,<nearest_city_with_airport>,<country>
    <destination>,<nearest_city_with_airport>,<country>
    <destination>,<nearest_city_with_airport>,<country>
    <destination>,<nearest_city_with_airport>,<country>
    <destination>,<nearest_city_with_airport>,<country>
    <destination>,<nearest_city_with_airport>,<country>
    <destination>,<nearest_city_with_airport>,<country>
    <destination>,<nearest_city_with_airport>,<country>
    <destination>,<nearest_city_with_airport>,<country>
    Where <destination> is the name of the destination, <nearest_city_with_airport> is the nearest city with an airport, and <country> is the country of the destination.
    Make sure to exclude any commas in the destination or nearest_city_with_airport or country names.
    Try to suggest nearest city with an airport that are well-known and have international airports.
    """

    file_id = upload_file_to_open_ai('airports-code.json')

    if file_id:
        prompt += f"""\n\nHere is the file id for airports code of cities around the world: {file_id}
        Use this file as a reference to find the correct name of a nearest city with an airport for each destination.
        For example, do not provide a city and a country where the city does not have an airport, or this city and country does not exist together in the file.
        Also - use this file as a reference to find the correct name of the country for each destination.
        """

    response = send_prompt(prompt).split("\n")[:10]
    for destination in response:
        destination_name, destination_city, destination_country = destination.split(",")  # nopep8
        final_list.append((destination_name.strip(), destination_city.strip(), destination_country.strip()))  # nopep8

    return final_list


def get_daily_plan_for_destination(arrival_date_and_time: str, departure_date_and_time: str, trip_type: str, destination: str, country: str) -> str:

    updated_prompt = f"""
    I am going on a solo {trip_type} vacation to {destination}, {country}. My arrival date and time: {arrival_date_and_time}, my departure date and time: {departure_date_and_time}.
    I need you to generate a daily plan for this {trip_type} vacation in the given time and location.
    Do not include any other information in your response.
    The format should be:
    Day 1:
    <activity>
    <activity>
    ...
    Day 2:
    <activity>
    <activity>
    ...
    Day 3:
    <activity>
    <activity>
    ...
    Day N:
    <activity>
    <activity>
    ...
    4 Best Moments:
    <moment>
    <moment>
    <moment>
    <moment>

    Here are some guidance:
    Each <activity> is an activity that can be done in the location or nearby at the specified time of year.
    I put 2 activity tags in each day, but you can put less or more depending on the time it takes to do them.
    N is the number of days in the trip.
    The 4 <moment> tags represents the 4 most thrilling, exciting, beautiful and fun activities (out of the activities you provided) which represents the best potential moments of the vacation.

    Do not make the list with bullets or dashes.

    Some considerations:
    Take into consideration the time of the day when the arrival and departure are.
    Make sure to include a variety of activities that cater to different interests and preferences.
    Also notice that like any other human - I need to eat, and sleep. So make sure to include some relaxing activities and time to eat (breakfast, lunch and dinner) and sleep.
    """

    response = send_prompt(updated_prompt)
    return response


def find_airport_code(city: str, country: str) -> str:
    with open('airports-code.json', 'r') as file:
        airport_codes = json.load(file)
    destination_airport_code = None
    fixed_city = get_normal_name_without_foreign_chars(city)
    fixed_country = get_normal_name_without_foreign_chars(country)
    for airport in airport_codes:
        if (fixed_city.lower().strip() in airport['city_name'].lower().strip()
                or airport['city_name'].lower().strip() in fixed_city.lower().strip()
                or fixed_city.lower().strip() in airport['airport_name'].lower().strip()) and \
                (fixed_country.lower().strip() in airport['country_name'].lower().strip() or airport['country_name'].lower().strip() in fixed_country.lower().strip() or fixed_country.lower().strip() in airport['country_code'].lower().strip() or airport['country_code'].lower().strip() in fixed_country.lower().strip()):
            destination_airport_code = airport['column_1']
            break
    if destination_airport_code:
        return destination_airport_code
    else:
        return ''


def search_flights(destinations: list, start_date: str, end_date: str, budget: int) -> dict:
    flights = {}
    for destination in destinations:

        destination_city = destination[1]
        destination_country = destination[2]
        destination_airport_code = None
        destination_airport_code = find_airport_code(
            destination_city, destination_country)
        if destination_airport_code == '':
            print(f"Could not find airport code for {destination_city}, {destination_country}")  # nopep8
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
        # Perform the flight search and store the results
        results = flight_search.get_dict()

        # Check if there was an error with the flight search
        if 'error' in results.keys():
            print(
                f"Error from serpapi: from TLV to {destination[0]} {destination[1]} {destination[2]}")
            continue
        elif 'best_flights' in results.keys():
            from_TLV_cheapest_flight = results['best_flights'][0]

        # else
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
        # Perform the flight search and store the results
        results = flight_search.get_dict()

        # Check if there was an error with the flight search
        if 'error' in results.keys():
            print(
                f"Error from serpapi: from {destination[0]} {destination[1]} {destination[2]} to TLV")
            continue

        elif 'best_flights' in results.keys():
            to_TLV_cheapest_flight = results['best_flights'][0]

        # else
        else:
            to_TLV_cheapest_flight = results['other_flights'][0]

        # check if sum of the two flights prices is within budget
        total_flights_price = from_TLV_cheapest_flight['price'] + to_TLV_cheapest_flight['price']  # nopep8
        if total_flights_price > budget:  # nopep8
            print(
                f"Total price of flights to {destination_city}, {destination_country} and back is above budget")
            continue

        fixed_destination = get_normal_name_without_foreign_chars(
            destination[0])
        fixed_city = get_normal_name_without_foreign_chars(destination[1])
        fixed_country = get_normal_name_without_foreign_chars(destination[2])

        flights['@'.join((fixed_destination, fixed_city, fixed_country))] = [[from_TLV_cheapest_flight, to_TLV_cheapest_flight], budget - total_flights_price]  # nopep8

    return flights


def search_hotels(destinations: dict, start_date: str, end_date: str) -> dict:
    hotels = {}
    for key, destination in destinations.items():
        destination_name = key.split('@')[0]
        destination_country = key.split('@')[2]
        hotel_search_params = {
            "engine": "google_hotels",
            "q": f"{destination_name}, {destination_country}",
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
            hotels[key] = [results['properties'], destination[1]]  # nopep8
    return hotels


def get_most_expensive_hotels(hotels: dict) -> dict:
    max_hotel = {}
    for key, hotels_and_leftover_budget in hotels.items():
        max_price = 0
        if hotels_and_leftover_budget is None:
            continue
        for hotel in hotels_and_leftover_budget[0]:
            if 'total_rate' not in hotel.keys():
                continue
            hotel_price = hotel['total_rate']['extracted_lowest']
            if hotel_price > max_price and hotels_and_leftover_budget[1] >= hotel_price:  # nopep8
                max_price = hotel_price
                max_hotel[key] = hotel

    return max_hotel


def get_dalle_images(activity: str, country: str) -> str:
    prompt = f"""I am going to a solo vacation to {country}, and I am going to do the following activity: {activity}.
    I could use your image generating skills to help me understand and feel the amazing moment I am going to have.
    Please generate an image of the activity. Make sure it looks real - don't exaggerate...
    Also - the image should not focus on me, only focus on the activity and maybe people that are needed for the activity (such as a show performers or an instructor, etc)."""

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


def get_top_5_options(begda: str, endda: str, trip_type: str, budget: int):
    # begda and endda are in the format of "YYYY-MM-DD"

    # get the top destinations
    destinations = get_top_destinations(int(begda.split("-")[1]), int(endda.split("-")[1]), trip_type)  # nopep8
    print('destinations: ' + str(destinations))
    # search for flights
    flights: dict = search_flights(destinations, begda, endda, budget)

    # search for hotels
    hotels: dict = search_hotels(flights, begda, endda)

    # get the most expensive hotels
    most_expensive_hotels: dict = get_most_expensive_hotels(hotels)

    final_list: dict = {key: {} for key in most_expensive_hotels.keys()}

    for key in final_list.keys():

        # destination details
        final_list[key]['destination'] = str(key.split('@')[0])
        final_list[key]['city'] = str(key.split('@')[1])
        final_list[key]['country'] = str(key.split('@')[2])

        # flights details
        final_list[key]['arrival_daytime'] = str(flights[key][0][0]['flights'][len(flights[key][0][0]['flights']) - 1]['arrival_airport']['time'])  # nopep8
        final_list[key]['arrival_total_price'] = float(flights[key][0][0]['price'])  # nopep8
        final_list[key]['arrival_connections_number'] = str(len(flights[key][0][0]['flights']) - 1)  # nopep8
        final_list[key]['arrival_connections_list'] = [str(get_normal_name_without_foreign_chars(flight['arrival_airport']['name'])) for flight in flights[key][0][0]['flights'][:-1]]  # nopep8
        final_list[key]['departure_daytime'] = str(flights[key][0][1]['flights'][0]['departure_airport']['time'])  # nopep8
        final_list[key]['departure_total_price'] = float(flights[key][0][1]['price'])  # nopep8
        final_list[key]['departure_connections_number'] = str(len(flights[key][0][1]['flights']) - 1)  # nopep8
        final_list[key]['departure_connections_list'] = [str(get_normal_name_without_foreign_chars(flight['departure_airport']['name'])) for flight in flights[key][0][1]['flights'][1:]]  # nopep8
        final_list[key]['flights_total_price'] = float(final_list[key]['arrival_total_price'] + final_list[key]['departure_total_price'])  # nopep8

        # hotels details
        final_list[key]['hotel_name'] = str(get_normal_name_without_foreign_chars(most_expensive_hotels[key]['name']))  # nopep8
        final_list[key]['hotel_total_price'] = float(most_expensive_hotels[key]['total_rate']['extracted_lowest'])  # nopep8

    print(final_list)
    return {k: final_list[k] for i, k in enumerate(final_list) if i < 5}


def get_daily_plan_and_images(arrival_date: str, departure_date: str, trip_type: str, destination: str, country: str):
    # get the daily plan
    daily_plan = get_daily_plan_for_destination(arrival_date, departure_date, trip_type, destination, country)  # nopep8
    print(daily_plan)
    activities = daily_plan.splitlines()[-4:]
    images = []
    for activity in activities:
        image_url = get_dalle_images(activity, country)
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
def get_top_5_options_route(start_date: str, end_date: str, trip_type: str, budget: int):
    try:
        return get_top_5_options(start_date, end_date, trip_type, budget)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/daily-plan-and-images")
def get_daily_plan_and_images_route(arrival_date: str, departure_date: str, trip_type: str, destination: str, country: str):
    try:
        return get_daily_plan_and_images(arrival_date, departure_date, trip_type, destination, country)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
