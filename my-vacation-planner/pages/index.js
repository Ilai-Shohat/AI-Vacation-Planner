import { useState } from 'react';
import axios from 'axios';
import 'react-dates/initialize';
import { DateRangePicker } from 'react-dates';
import 'react-dates/lib/css/_datepicker.css';
import Head from 'next/head';

export default function Home() {
  const [startDate, setStartDate] = useState(null);
  const [endDate, setEndDate] = useState(null);
  const [focusedInput, setFocusedInput] = useState(null);
  const [tripType, setTripType] = useState('');
  const [budget, setBudget] = useState('');
  const [destinations, setDestinations] = useState({});
  const [loadingDestinations, setLoadingDestinations] = useState(false);
  const [loadingDailyPlanAndImages, setLoadingDailyPlanAndImages] = useState(false);
  const [showButton, setShowButton] = useState(true);
  const [showDestinations, setShowDestinations] = useState(true);
  const [showDailyPlan, setShowDailyPlan] = useState(false);
  const [dailyPlanAndImagesLinks, setDailyPlanAndImagesLinks] = useState({});


  const getDestinations = async () => {
    if (!startDate || !endDate) {
      alert('Please select both start and end dates');
      return;
    }

    if (!tripType) {
      alert('Please select a trip type');
      return;
    }

    setShowButton(false);
    setShowDestinations(true);

    setLoadingDestinations(true);
    try {

      const response = await axios.get(`http://127.0.0.1:8000/top-5-options?start_date=${startDate.format('YYYY-MM-DD')}&end_date=${endDate.format('YYYY-MM-DD')}&trip_type=${tripType}&budget=${budget}`);
      setDestinations(response.data);
    } catch (error) {
      console.error(error);
    } finally {
      setLoadingDestinations(false);
    }

  };

  const getDailyPlanAndImages = async (key) => {

    // at this point, the state "destinations" should have the selected destination as the only key in the object
    setLoadingDailyPlanAndImages(true);
    try {
      const response = await axios.get(`http://127.0.0.1:8000/daily-plan-and-images?arrival_date=${startDate.format('YYYY-MM-DD')}&departure_date=${endDate.format('YYYY-MM-DD')}&trip_type=${tripType}&destination=${destinations[key].destination}&country=${destinations[key].country}`);
      setDailyPlanAndImagesLinks(response.data);
    } catch (error) {
      console.error(error);
    } finally {
      setLoadingDailyPlanAndImages(false);
      setShowDailyPlan(true);
    }
  };

  const handleClick = (key) => {
    console.log(key);
    setDestinations({ [key]: destinations[key] });
    getDailyPlanAndImages(key);
  };

  // Update the event handlers to show the button again when any input changes
  const handleInputChange = (setter) => (e) => {
    setter(e.target.value);
    setShowButton(true); // Show the button
    setShowDestinations(false);
    setShowDailyPlan(false);
  };

  // Update the onDatesChange handler to show the button again when dates change
  const handleDatesChange = ({ startDate, endDate }) => {
    setStartDate(startDate);
    setEndDate(endDate);
    setShowButton(true); // Show the button
    setShowDestinations(false);
    setShowDailyPlan(false);
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (parseInt(budget, 10) <= 0 || isNaN(parseInt(budget, 10))) {
      alert('Please enter a budget greater than 0');
      return;
    }
    getDestinations();
  };


  return (
    <>
      <Head>
        <link href="https://fonts.googleapis.com/css2?family=Rubik:wght@400;500;700&display=swap" rel="stylesheet" />
      </Head>
      <div>
        <h1>AI Trip Planner</h1>
        <div className="form-container">
          <form onSubmit={handleSubmit}>
            <label className="form-label">
              Trip type:
              <select className="form-input" value={tripType} onChange={handleInputChange(setTripType)} required>
                <option value="" disabled>Select trip type</option>
                <option value="ski">Ski</option>
                <option value="beach">Beach</option>
                <option value="city">City</option>
                <option value="adventure">Adventure</option>
                <option value="cruise">Cruise</option>
                <option value="camping">Camping</option>
                <option value="luxury">Luxury</option>
                <option value="culinary">Culinary</option>
              </select>
            </label>
            <label className="form-label">
              Budget:
              <input className="form-input" style={{ width: "5em" }} type="number" value={budget} onChange={handleInputChange(setBudget)} required min="1" />
            </label>
            <label className="form-label">
              Date range:
              <DateRangePicker
                startDate={startDate}
                startDateId="your_unique_start_date_id"
                endDate={endDate}
                endDateId="your_unique_end_date_id"
                onDatesChange={handleDatesChange}
                focusedInput={focusedInput}
                onFocusChange={(focusedInput) => setFocusedInput(focusedInput)}
                displayFormat="YYYY-MM-DD"
                startDatePlaceholderText="yyyy-mm-dd"
                endDatePlaceholderText="yyyy-mm-dd"
              />
            </label>

            {showButton && (
              <div className="button-container">
                <button className="submit-button" type="submit">Get Destinations</button>
              </div>
            )}
          </form>
        </div>

        {loadingDestinations && <p className="loading-text">Loading...</p>}
        {showDestinations && (
          <div className="button-group">
            {Object.entries(destinations).map(([key, destination], index) => (
              <button key={index} onClick={() => handleClick(key)}>
                <span className="headline">{destination.destination}, {destination.city}, {destination.country}</span> <br />
                {destination.arrival_connections_list.length > 0 && (
                  <>
                    <span className="underline">First way flights connections:</span> {destination.arrival_connections_list.join(', ')} <br />
                    <br />
                  </>
                )}
                <span className="underline">Arrival time to destination:</span> {destination.arrival_daytime} <br />
                <br />
                {destination.departure_connections_list.length > 0 && (
                  <>
                    <span className="underline">Second way flights connections:</span> {destination.departure_connections_list.join(', ')} <br />
                    <br />
                  </>
                )}
                <span className="underline">Departure time:</span> {destination.departure_daytime} <br />
                <br />
                <span className="underline">Total flights costs:</span> {destination.flights_total_price} $ <br />
                <br />
                <span className="underline">Hotel:</span> {destination.hotel_name} <br />
                <br />
                <span className="underline">Total hotel price:</span> {destination.hotel_total_price} $ <br />
                <br />
                <span className="underline2">Total trip cost:</span> <text className="totalPrice">{destination.flights_total_price + destination.hotel_total_price} $</text>
              </button>
            ))}
          </div>
        )}
        {loadingDailyPlanAndImages && <p className="loading-text">Loading...</p>}
        {showDailyPlan && (
          <div className="daily-plan-and-images-container" style={{ display: 'flex', justifyContent: 'space-around' }}>
            <div className='daily-plan'>
              <h2 style={{ textAlign: 'center' }}>Daily Plan</h2>
              {Object.entries(dailyPlanAndImagesLinks.daily_plan).map(([key, value], index) => (
                <div style={{ marginTop: 20 }}>
                  <span style={{ marginBottom: 5, textDecoration: 'underline' }}>Day {key}:<br /></span>
                  {value.map((item, index) => (
                    <li key={index}>{item}</li>
                  ))}
                </div>
              ))}
            </div>
            <div className='images'>
              <h2 style={{ textAlign: 'center' }}>Images</h2>
              {dailyPlanAndImagesLinks.images.map((image, index) => (
                <img key={index} src={image} alt={`Image ${index}`} width={256} height={256} />
              ))}
            </div>
          </div>
        )}

      </div>
    </>
  );
}