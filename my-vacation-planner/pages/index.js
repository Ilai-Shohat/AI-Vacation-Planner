import { useState } from 'react';
import axios from 'axios';
import 'react-dates/initialize';
import { DateRangePicker } from 'react-dates';
import 'react-dates/lib/css/_datepicker.css';
import 'bootstrap/dist/css/bootstrap.min.css';
import Head from 'next/head';

export default function Home() {
  const [startDate, setStartDate] = useState(null);
  const [endDate, setEndDate] = useState(null);
  const [focusedInput, setFocusedInput] = useState(null);
  const [tripType, setTripType] = useState('');
  const [budget, setBudget] = useState('');
  const [showForm, setShowForm] = useState(true);
  const [destinations, setDestinations] = useState({});
  const [loadingDestinations, setLoadingDestinations] = useState(false);
  const [loadingDailyPlanAndImages, setLoadingDailyPlanAndImages] = useState(false);
  const [showButton, setShowButton] = useState(true);
  const [showDestinations, setShowDestinations] = useState(true);
  const [showDailyPlan, setShowDailyPlan] = useState(false);
  const [dailyPlanAndImagesLinks, setDailyPlanAndImagesLinks] = useState({});

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

  const handleClick = (key) => {
    console.log(key);
    setDestinations({ [key]: destinations[key] });
    getDailyPlanAndImages(key);
  };

  const getDestinations = async () => {
    if (!startDate || !endDate) {
      alert('Please select both start and end dates');
      return;
    }

    if (!tripType) {
      alert('Please select a trip type');
      return;
    }

    if (!budget) {
      alert('Please enter a budget');
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
      setShowForm(false);
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

  return (
    <>
      <Head>
        <link href="https://maxcdn.bootstrapcdn.com/bootstrap/4.0.0/css/bootstrap.min.css" rel="stylesheet" />
        <link href="https://fonts.googleapis.com/css2?family=Montserrat:ital,wght@0,100..900;1,100..900&display=swap" rel="stylesheet"></link>
      </Head>
      <div class="navbar navbar-expand-lg navbar-dark bg-primary">
        <nav class="navbar navbar-expand-lg navbar-dark bg-primary">
          <a class="navbar-brand" >A.I TRIP PLANNER</a>
        </nav>
      </div>
      <div className="container-fluid mt-5">
        {showForm && (
          <div className="card">
            <div className="card-body">
              <h2 className="card-title">Plan Your Next Trip With The Power Of AI!</h2>
              <form onSubmit={handleSubmit}>
                <div className="form-row">

                  <div className="form-group col-md-4">
                    <label className="form-label">Trip type:</label>
                    <select className="form-control" value={tripType} onChange={handleInputChange(setTripType)} required>
                      <option value="" disabled>Select trip type</option>
                      <option value="ski">Ski</option>
                      <option value="beach">Beach</option>
                      <option value="city">City</option>
                    </select>
                  </div>

                  <div className="form-group col-md-4">
                    <label className="form-label">Date range:</label>
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
                  </div>

                  <div className="form-group col-md-4">
                    <label className="form-label">Budget ($):</label>
                    <input className="form-control"
                      type="number"
                      value={budget}
                      onChange={handleInputChange(setBudget)}
                      required
                      min="1" />
                  </div>
                </div>
                {showButton && (
                  <div className="button-container">
                    <button className="btn btn-primary btn-block" type="submit">Get Destinations Suggestions</button>
                  </div>
                )}
              </form>
            </div>
          </div>)}

          {loadingDestinations &&
            <div className="loading-spinner">
              <div className="spinner-border text-primary" role="status">
                <span className="sr-only">Loading...</span>
              </div>
            </div>}
          {showDestinations && (
            <div className="container mt-5 button-group">
              {Object.entries(destinations).map(([key, destination], index) => (
                <button className="btn btn-primary" key={index} onClick={() => handleClick(key)}>
                  <span className="headline">{destination.destination}</span> <br />
                  {destination.arrival_connections_list.length > 0 && (
                    <>
                      <span className="underline">First way flights connections:</span><br /> {destination.arrival_connections_list.join(', ')} <br />
                      <br />
                    </>
                  )}
                  <span className="underline">Arrival time to destination:</span><br /> {destination.arrival_daytime} <br />
                  <br />
                  {destination.departure_connections_list.length > 0 && (
                    <>
                      <span className="underline">Second way flights connections:</span><br /> {destination.departure_connections_list.join(', ')} <br />
                      <br />
                    </>
                  )}
                  <span className="underline">Departure time:</span><br /> {destination.departure_daytime} <br />
                  <br />
                  <span className="underline">Total flights costs:</span><br /> {destination.flights_total_price} $ <br />
                  <br />
                  <span className="underline">Hotel:</span><br /> {destination.hotel_name} <br />
                  <br />
                  <span className="underline">Total hotel price:</span><br /> {destination.hotel_total_price} $ <br />
                  <br />
                  <span className="underline2">Total trip cost:</span><br /> <text className="totalPrice">{destination.flights_total_price + destination.hotel_total_price} $</text>
                </button>
              ))}
            </div>
          )}
          {loadingDailyPlanAndImages &&
            <div className="loading-spinner">
              <div className="spinner-border text-primary" role="status">
                <span className="sr-only">Loading...</span>
              </div>
            </div>}
          {showDailyPlan && (
            <div className="daily-plan-and-images-container">
              <div className='daily-plan'>
                <h2 style={{ textAlign: 'center' }}>Daily Plan</h2>
                {Object.entries(dailyPlanAndImagesLinks.daily_plan).map(([key, value], index) => (
                  <div key={index}>
                    <span>Day {key}:</span>
                    {value.map((item, itemIndex) => (
                      <li key={itemIndex}>{item}</li>
                    ))}
                    {index < Object.entries(dailyPlanAndImagesLinks.daily_plan).length - 1 && (
                      <hr />
                    )}
                  </div>
                ))}
              </div>
              <div className='images'>
                {dailyPlanAndImagesLinks.images.map((image, index) => (
                  <img key={index} src={image} alt={`Image ${index}`} />
                ))}
              </div>
            </div>
          )}
        </div>

      </div >
    </>
  );
}