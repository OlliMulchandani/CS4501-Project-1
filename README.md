Download your Google Takeout and extract the .zip in the same directory as analyze.py and run. Of course, I did not include my Google Takeout data in this public repo as I probably have no data more private haha.

You must first uncomment the following lines and run the program to collect and cache your search history (it's a very slow step, and for debugging reasons, best not to have to run it every time):
``` python
# with open("Takeout/My Activity/Search/MyActivity.html", "r", encoding="utf-8") as f:
#     html_content = f.read()
# save_search_entries(html_content)
```
Then re-comment them for all future runs.
