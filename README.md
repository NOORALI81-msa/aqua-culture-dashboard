# Aqua-Culture Sales & Employee Tracking Dashboard

A full-stack web application built with Python and Flask to provide managers with a real-time dashboard for tracking field employee activity and sales performance.

**Live Demo Link:** [https://aqua-culture-dashboard.onrender.com](https://aqua-culture-dashboard.onrender.com) 🚀



---

## Features

* **Manager Dashboard:** An overview of Key Performance Indicators (KPIs) like total employees, total farmers, and monthly sales.
* **Interactive Sales Map:** Uses **Leaflet.js** to display a geographical heatmap of sales concentration, allowing for easy identification of top-performing areas.
* **Data Visualization:** Integrates **Chart.js** to render interactive bar charts of daily and monthly sales performance by employee.
* **Employee Status Tracking:** A real-time table showing employee status, kilometers covered, and last known location.
* **Responsive Design:** A clean and modern UI that works on both desktop and mobile devices.

---

## Technology Stack

* **Backend:** Python, Flask, Gunicorn
* **Frontend:** HTML, CSS, JavaScript
* **Mapping:** [Leaflet.js](https://leafletjs.com/) & [leaflet-heat](https://github.com/Leaflet/Leaflet.heat)
* **Charts:** [Chart.js](https://www.chartjs.org/)
* **Database:** SQLite (or specify your database, e.g., PostgreSQL)
* **Deployment:** Render

---

## Setup and Local Installation

To run this project on your local machine, follow these steps:

1.  **Clone the Repository**
    ```sh
    git clone [https://github.com/your-username/your-repository-name.git](https://github.com/NOORALI-msa/aqua-culture-dashboard.git)
    cd your-repository-name
    ```

2.  **Create and Activate a Virtual Environment**
    *This is highly recommended to keep project dependencies isolated.*
    ```sh
    # Create the virtual environment
    python -m venv venv

    # Activate it
    # On Windows:
    venv\Scripts\activate
    # On macOS/Linux:
    source venv/bin/activate
    ```

3.  **Install Dependencies**
    *Install all the packages listed in the `requirements.txt` file.*
    ```sh
    pip install -r requirements.txt
    ```

4.  **Run the Application**
    *Use the Flask development server to start the app.*
    ```sh
    flask run
    ```
    The application will be available at `http://127.0.0.1:5000` in your web browser.