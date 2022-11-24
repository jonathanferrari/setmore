import requests, os, dotenv, json, time
import numpy as np, pandas as pd
from IPython import *
from IPython.display import *
from ipywidgets import *
import plotly.express as px, plotly.figure_factory as ff

dotenv.load_dotenv()


email = "bffs@berkeley.edu"
base = "https://developer.setmore.com/api/v1"


def appt_json_to_df(appts):
    df = pd.DataFrame(appts)
    df["start"] = pd.to_datetime(df.start_time)
    df = df.set_index("key", drop = True)
    df = df.drop(columns = ["start_time", "end_time", "staff_key", "service_key"])
    df["staff"] = df.staff.str.split("(").str[0]
    df["service"] = df.service.str.split("]").str[0].str[1:]
    df["time"] = df.start.apply(lambda x: x.time().strftime("%I:%M %p"))
    df["month"] = df.start.apply(lambda x: x.date().strftime("%B"))
    df["weekday"] = df.start.apply(lambda x: x.date().strftime("%A"))
    return df

def get_refresh_token():
    refresh_token = os.getenv("REFRESH_TOKEN")
    refresh_token_link = f"{base}/o/oauth2/token?refreshToken={refresh_token}"
    token = requests.get(refresh_token_link).json()["data"]['token']['access_token']
    return token

bearer = get_refresh_token()

def setmore_get(service):
    result = requests.get(url = f'{base}/{service}',headers = { 'Content-Type': 'application/json',
                                                                'Authorization': f'Bearer {bearer}'
                                                              })
    try:
        return result.json()["data"]
    except Exception:
        print(service)
        return result.json()
    
  


def get_services():
    services =  setmore_get("bookingpage/services")["services"]
    service_dict = {service["key"] : service["service_name"] for service in services}
    return service_dict

def get_staff():
    return setmore_get("bookingapi/staffs")

def get_appointments(start, end, cursor = None):
    staff = read("staff")
    services = read("services")
    cursor = f"&cursor={cursor}" if cursor else ""
    new_cursor = None
    appts = setmore_get(f"bookingapi/appointments?startDate={start}{cursor}&endDate={end}&customerDetails=true")
    try:
        if "cursor" in appts:
            new_cursor = appts["cursor"]
        appts = appts["appointments"]
        appointments = []
        for a in appts:
            apt = {k: a[k] for k in ('key', "staff_key" , 'service_key', 'start_time', 'end_time', "duration")}
            apt["staff"] = staff.get(a["staff_key"], a["staff_key"])
            apt['service'] = services.get(a["service_key"], a["service_key"])
            appointments += [apt]
    except Exception as e:
        try:
            globals()['bearer'] = get_refresh_token()
            return get_appointments(start, end, cursor if (cursor != "") else None)
        except Exception as e:
            print(e)
            return appts
    appointments = appt_json_to_df(appointments)
    if new_cursor and (new_cursor != cursor):
        new_appts = get_appointments(start, end, new_cursor)
        appointments = pd.concat([appointments, new_appts])
    appointments["length"] = appointments.duration.apply(lambda x: "Half-Hour" if x == 30 else "Hour")
    appointments = appointments.drop(columns = ["duration"])
    #appointments.columns = ['Peer', 'Type', 'Start', 'Time', 'Month', 'Weekday', 'Length']
    return appointments

def write_staff_dict():
    staff = get_staff()["staffs"]
    staff = [{"key" : s["key"], "name" : s["first_name"] + " " + s["last_name"]} for s in staff]
    staff = {staff[i]["key"] : staff[i]["name"] for i in range(len(staff))}
    write(staff, "staff")
    
def write_services_dict():
    services = get_services()
    write(services, "services")

#####################
# GENERAL UTILITIES #
#####################

def write(dic: dict, fp: str, full_fp: bool = False) -> None:
    """
    ### Write a dictionary to a JSON file

    Parameters
    ----------
    dic : `dict`
        The dictionary to be written
    fp : `str`
        The filepath to write the dictionary to
        such that file is named `data/json/<fp>.json`
    full_fp : `bool`
        Whether the filepath is the full filepath or not

    Returns
    -------
    `None`
    """
    if not full_fp:
        fp = f"data/json/{fp}.json"
    json.dump(dic, open(fp, "w"), indent=4)


def read(fp: str, full_fp: bool = False) -> dict:
    """
    ### Creates a dictionary of the given JSON file

    Parameters
    ----------
    fp : `str`
        The file path of the JSON file
        such that file is named `data/json/<fp>.json`

    full_fp : `bool`
        Whether the filepath is the full filepath or not

    Returns
    -------
    `dict`
        A dictionary of the JSON file

    Examples
    --------
    >>> read("example.json")
    {'a': 1, 'b': 2, 'c': 3}
    """
    if not full_fp:
        fp = f"data/json/{fp}.json"
    return json.load(open(fp, "r"))


def delay(n: int = 60, step: int = 5) -> None:
    """
    ### Sleeps for n seconds in steps of step seconds.
    Also prints countdown.

    Parameters
    ----------
    n : `int`, (optional | default = 60)
        How many seconds to sleep for.
    step : `int`, (optional | default = 5)
        How many seconds to sleep at once.

    Returns
    -------
    `None`
    """
    d = 0
    while d <= n:
        print(f"Sleeping for {n - d} seconds", end="\r")
        time.sleep(step)
        d += step
        
# fix column name errors
def plot(df):
    
    @interact(x = Dropdown(
        options = ["all", "date", 'staff', 'service', 'time', 'month', 'weekday', 'length'], 
        value = "all"
        )
    )
    def pick_plotter(x):
        date_vals = ["Line", "Strip", "Violin", "Histogram"]
        if x == "all":
            @interact(graph = Dropdown(options = date_vals, value = "Line"))
            def all_plot(graph):
                if graph == "Line":
                    fig = px.line(df, x = "start", 
                                  template = "seaborn", title = "Line Plot of Appointments")
                    fig.update_yaxes(visible=False, showticklabels=False)
                elif graph == "Violin":
                    fig = px.violin(df, x = "start", 
                                    template = "seaborn", title = "Violin Plot of Appointments")
                elif graph == "Strip":
                    fig = px.strip(df, x = "start", 
                                   template = "seaborn", title = "Strip Plot of Appointments")
                elif graph == "Histogram":
                    fig = px.histogram(df, x = "start", marginal="rug",
                                       template = "seaborn", title = "Histogram of Appointments")
                fig.show()
        elif x == "date":
            @interact(graph = Dropdown(options = date_vals, value = "Strip"))
            def date_plot_by_staff(graph):
                if graph == "Line":
                    fig = px.line(df, x = "start", color = "staff", 
                                  template = "seaborn", title = "Line Plot of Appointments by Peer")
                    fig.update_yaxes(visible=False, showticklabels=False)
                elif graph == "Violin":
                    fig = px.violin(df, y = "start", color = "staff", 
                                    template = "seaborn", title = "Violin Plot of Appointments by Peer")
                elif graph == "Strip":
                    fig = px.strip(df, x = "start", color = "staff", y = "staff", 
                                   template = "seaborn", title = "Strip Plot of Appointments by Peer")
                elif graph == "Histogram":
                    fig = px.histogram(df, x = "start", color = "staff", marginal="rug", barmode = "overlay", 
                                       template = "seaborn", title = "Histogram of Appointments by Peer")
                fig.show()
        else:
            @interact(graph = Dropdown(options = ["Bar", "Pie"], value = "Bar"))
            def visualize(graph):
                title = f"{graph} Chart of {x} of Appointments"
                if graph == "Bar":
                    fig = px.histogram(df, x, 
                                    template = "seaborn", color = x, title = title)
                    fig = fig.update_xaxes(categoryorder = "total descending")
                else:
                    fig = px.pie(df, x, template = "seaborn", title = title)
                #fig.update_layout(width = 1600, height = 800)
                fig.show()