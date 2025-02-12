from click import group
import pytz
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import re
from collections import defaultdict
import matplotlib.pyplot as plt

###############################
# 1. Data Extraction Functions
###############################

def save_search_entries(html_content, output_file="cached_entries.txt"):
    """
    One-time function to extract and save search entries from your HTML.
    Writes each entry's text to 'cached_entries.txt', separated by a line '---END_ENTRY---'.
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    search_entries = soup.find_all('div', class_='outer-cell mdl-cell mdl-cell--12-col mdl-shadow--2dp')
    
    with open(output_file, 'w', encoding='utf-8') as f:
        for entry in search_entries:
            content_cell = entry.find('div', class_='content-cell mdl-cell mdl-cell--6-col mdl-typography--body-1')
            if content_cell:
                f.write(content_cell.get_text(strip=True) + '\n---END_ENTRY---\n')

def parse_search_history(input_source, start_year=2025, use_cache=True):
    """
    Parses the cached_entries.txt (or original HTML) and returns a list of datetime
    objects (in US/Eastern timezone) for all search timestamps in or after 'start_year'.
    """
    est_tz = pytz.timezone("US/Eastern")
    start_date = datetime(start_year, 1, 1).replace(tzinfo=est_tz)
    timestamps = []
    
    if use_cache:
        # Read from cached file
        with open("cached_entries.txt", 'r', encoding='utf-8') as f:
            content = f.read()
            entries = content.split('---END_ENTRY---\n')
    else:
        # Parse directly from the provided HTML content
        soup = BeautifulSoup(input_source, 'html.parser')
        search_entries = soup.find_all('div', class_='outer-cell mdl-cell mdl-cell--12-col mdl-shadow--2dp')
        entries = [
            entry.find('div', class_='content-cell mdl-cell mdl-cell--6-col mdl-typography--body-1').get_text(strip=True)
            for entry in search_entries
            if entry.find('div', class_='content-cell mdl-cell--6-col mdl-typography--body-1')
        ]

    # Regex for matching a date string like "Feb 8, 2025, 3:35:23 PM EST"
    date_pattern = re.compile(r'([A-Z][a-z]{2} \d{1,2}, \d{4}, \d{1,2}:\d{2}:\d{2} [AP]M EST)')

    for text in entries:
        # Replace any non-breaking spaces with regular spaces.
        text_cleaned = text.replace(' ', ' ')
        match = date_pattern.search(text_cleaned)
        if not match:
            continue

        date_str = match.group(1)
        try:
            dt = datetime.strptime(date_str, '%b %d, %Y, %I:%M:%S %p EST')
            dt = est_tz.localize(dt)
            if dt.year < start_year:
                continue
            if dt >= start_date:
                timestamps.append(dt)
        except ValueError as e:
            print(f"Couldn't parse date: {date_str} - {e}")
            continue

    return timestamps

def time_diff(start, end):
    """Compute difference in hours, adjusting for crossing midnight."""
    diff = end - start
    if diff < 0:
        diff += 24
    return diff

###############################
# 2. Load and Parse the Data
###############################

# Uncomment the next lines to create the cache if needed.
# with open("Takeout/My Activity/Search/MyActivity.html", "r", encoding="utf-8") as f:
#     html_content = f.read()
# save_search_entries(html_content)

# Get the list of timestamp objects.
timestamps = parse_search_history("cached_entries.txt", use_cache=True)

#########################################
# 3. Grouping for Sleep Gap Calculations
#########################################

# For sleep calculation, we shift searches before 3AM into the previous "sleep day".
sleep_grouping = defaultdict(list)
for dt in timestamps:
    # If dt.hour < 3, subtract 3 hours so it groups with the previous day.
    sleep_day = (dt - timedelta(hours=3)).date() if dt.hour < 3 else dt.date()
    sleep_grouping[sleep_day].append(dt)

# Compute sleep statistics per sleep_group.
sleep_stats = {}
for day, day_searches in sorted(sleep_grouping.items()):
    day_searches.sort()
    first_search = day_searches[0]
    last_search = day_searches[-1]
    count = len(day_searches)
    sleep_stats[day] = {'count': count, 'first': first_search, 'last': last_search}
    print(f"{day}: Count = {count}, First search = {first_search.strftime('%H:%M:%S')}, Last search = {last_search.strftime('%H:%M:%S')}")


# Estimate sleep gaps using the sleep grouping.
sorted_sleep_days = sorted(sleep_stats.keys())
print("Sleep Gap Estimates (using shifted grouping):")
for i in range(len(sorted_sleep_days) - 1):
    current_day = sorted_sleep_days[i]
    next_day = sorted_sleep_days[i + 1]
    last_search_current = sleep_stats[current_day]['last']
    first_search_next = sleep_stats[next_day]['first']
    gap_hours = (first_search_next - last_search_current).total_seconds() / 3600.0
    print(f"Between sleep group {current_day} and {next_day}: approx. {gap_hours:.2f} hours gap")

#########################################
# 4. Grouping for Plotting (Actual Date)
#########################################

# For plotting we use the actual calendar date.
actual_grouping = defaultdict(list)
for dt in timestamps:
    actual_day = dt.date()
    actual_grouping[actual_day].append(dt)

# Compute plotting statistics per actual day.
plot_stats = {}
for day, day_searches in sorted(actual_grouping.items()):
    day_searches.sort()
    first_search = day_searches[0]
    last_search = day_searches[-1]
    count = len(day_searches)
    plot_stats[day] = {'count': count, 'first': first_search, 'last': last_search}

#########################################
# 5. Plotting the Data
#########################################

weekday_wake_times = []
weekday_sleep_times = []
weekend_wake_times = []
weekend_sleep_times = []

sorted_actual_days = sorted(plot_stats.keys())

fig, ax = plt.subplots(figsize=(12, len(sorted_actual_days)*0.2 + 2))
yticks = []
ylabels = []

for i, day in enumerate(sorted_actual_days):
    day_searches = actual_grouping[day]
    day_searches.sort()

    first_search = plot_stats[day]['first']
    last_search  = plot_stats[day]['last']

    # Compute hours for the first and last search.
    first_hour = first_search.hour + first_search.minute/60 + first_search.second/3600
    last_hour  = last_search.hour + last_search.minute/60 + last_search.second/3600

    # --- Sleep Shading ---

    # Morning sleep shading
    if first_hour > 3:
        # Assume sleeping from midnight until the first search.
        ax.broken_barh([(0, first_hour)], (i - 0.2, 0.4), facecolors='lightblue', alpha=0.3)
    else:
        # For early-morning searches, use sleep grouping to determine wake time.
        try:
            last_night_sleep = sleep_stats[day - timedelta(days=1)]['last']
            last_night_sleep_hour = last_night_sleep.hour + last_night_sleep.minute/60 + last_night_sleep.second/3600
            today_wake = sleep_stats[day]['first']
            today_wake_hour = today_wake.hour + today_wake.minute/60 + today_wake.second/3600
            ax.broken_barh([(last_night_sleep_hour, today_wake_hour - last_night_sleep_hour)], (i - 0.2, 0.4), facecolors='lightblue', alpha=0.3)
        except KeyError:
            # Fallback in case the sleep_stats key isn't available.
            ax.broken_barh([(0, first_hour)], (i - 0.2, 0.4), facecolors='lightblue', alpha=0.3)

    # Evening sleep shading
    # Use sleep_stats to determine when sleep began.
    try:
        today_sleep = sleep_stats[day]['last']
        today_sleep_hour = today_sleep.hour + today_sleep.minute/60 + today_sleep.second/3600
    except KeyError:
        today_sleep_hour = last_hour

    if today_sleep_hour > 3:
        ax.broken_barh([(last_hour, 24 - last_hour)], (i - 0.2, 0.4), facecolors='lightblue', alpha=0.3)

    # --- Awake Shading ---
    # The awake period is defined as the gap between the sleep periods.
    # For the start of the awake period:
    if first_hour > 3:
        awake_start = first_hour
    else:
        try:
            # If there were early searches, use the sleep grouping’s first search as wake time.
            today_wake = sleep_stats[day]['first']
            awake_start = today_wake.hour + today_wake.minute/60 + today_wake.second/3600
            ax.broken_barh([(0, last_night_sleep_hour)], (i - 0.2, 0.4), facecolors='peachpuff', alpha=0.3)
        except KeyError:
            awake_start = first_hour

    # For the end of the awake period:
    if today_sleep_hour > 3:
        awake_end = last_hour        # Use the actual last search hour for shading.
        effective_bedtime = last_hour  # For averages, bedtime is just the time.
    else:
        awake_end = 24               # Plot shading until midnight.
        effective_bedtime = 24 + last_hour  # For averages, add 24 hours if bedtime is before 3 AM.

    # Save these times for average calculations.
    if day.weekday() in [4, 5, 6]:
        weekend_wake_times.append(awake_start)
        weekend_sleep_times.append(effective_bedtime)
    else:
        weekday_wake_times.append(awake_start)
        weekday_sleep_times.append(effective_bedtime)

    # Only plot if we have a valid (positive) interval.
    if awake_end > awake_start:
        ax.broken_barh([(awake_start, awake_end - awake_start)], (i - 0.2, 0.4), facecolors='peachpuff', alpha=0.3)

    # Plot each search as a black dot.
    for dt in day_searches:
        search_hour = dt.hour + dt.minute/60 + dt.second/3600
        ax.plot(search_hour, i, 'o', color='black')

    # Choose label formatting: use "%b %d" ("Jan 25")
    if day.weekday() in [4, 5, 6]:  # Friday=4, Saturday=5, Sunday=6
        label = r"$\bf{" + day.strftime("%b  %d") + "}$"
    else:
        label = day.strftime("%b %d")
    yticks.append(i)
    ylabels.append(label)

ax.set_yticks(yticks)
ax.set_yticklabels(ylabels)
ax.set_xlabel('Hour of Day')
ax.set_xlim(0, 24)
ax.set_title('Daily Search Activity and Sleep Estimates')

# --- Add vertical dotted lines for average wake and sleep times ---

# Calculate averages (they are in hours; effective_bedtime is already ≥ wake time)
if weekday_wake_times:
    avg_wake_weekday = sum(weekday_wake_times) / len(weekday_wake_times)
    avg_bed_weekday = sum(weekday_sleep_times) / len(weekday_sleep_times)
    # Compute average awake duration (i.e. time active during the day)
    avg_awake_duration_weekday = time_diff(avg_wake_weekday, avg_bed_weekday)
    # And compute sleep duration as the remainder of the day:
    avg_sleep_duration_weekday = 24 - avg_awake_duration_weekday
    ax.axvline(avg_wake_weekday, color='blue', linestyle='dotted', linewidth=1.5, label='Weekday Avg Wake and Sleep')
    ax.axvline(avg_bed_weekday, color='blue', linestyle='dotted', linewidth=1.5)
    

if weekend_wake_times:
    avg_wake_weekend = sum(weekend_wake_times) / len(weekend_wake_times)
    avg_bed_weekend = sum(weekend_sleep_times) / len(weekend_sleep_times)
    avg_awake_duration_weekend = time_diff(avg_wake_weekend, avg_bed_weekend)
    avg_sleep_duration_weekend = 24 - avg_awake_duration_weekend
    

# For display, if the bedtime average is >= 24, subtract 24 to show the proper time-of-day.
display_bed_weekday = avg_bed_weekday if avg_bed_weekday < 24 else avg_bed_weekday - 24
display_bed_weekend = avg_bed_weekend if avg_bed_weekend < 24 else avg_bed_weekend - 24
ax.axvline(avg_wake_weekend, color='orange', linestyle='dotted', linewidth=1.5, label='Weekend Avg Wake and Sleep')
ax.axvline(display_bed_weekend, color='orange', linestyle='dotted', linewidth=1.5)

def convert_to_12_hour_format(hours):
    total_seconds = int(hours * 3600) % (24*3600)  # Ensure we are within 0-24 hours.
    time_obj = (datetime.min + timedelta(seconds=total_seconds)).time()
    return time_obj.strftime("%I:%M %p")

def convert_to_hours_and_minutes(hours):
    total_seconds = int(hours * 3600) % (24*3600)  # Ensure we are within 0-24 hours.
    time_obj = (datetime.min + timedelta(seconds=total_seconds)).time()
    time_string = time_obj.strftime("%H:%M")
    return time_string

print("Weekday Avg Wake: ", convert_to_12_hour_format(avg_wake_weekday))
print("Weekday Avg Bedtime: ", convert_to_12_hour_format(display_bed_weekday))
print("Weekday Avg Awake Duration: ", convert_to_hours_and_minutes(avg_awake_duration_weekday))
print("Weekday Avg Sleep Duration: ", convert_to_hours_and_minutes(avg_sleep_duration_weekday))

print("Weekend Avg Wake: ", convert_to_12_hour_format(avg_wake_weekend))
print("Weekend Avg Bedtime: ", convert_to_12_hour_format(display_bed_weekend))
print("Weekend Avg Awake Duration: ", convert_to_hours_and_minutes(avg_awake_duration_weekend))
print("Weekend Avg Sleep Duration: ", convert_to_hours_and_minutes(avg_sleep_duration_weekend))


ax.legend(loc='upper right')
plt.tight_layout()
plt.savefig("daily_search_activity_correct.png")
plt.show()


