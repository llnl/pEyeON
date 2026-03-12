from dataclasses import dataclass

@dataclass
class Page:
    filename: str
    label: str
    

def app_pages():
    """
    Define metadata for pages used in this app.
    """
    return [Page("pages/EyeOnSummary.py", "EyeOn Summary"),
            Page("pages/BrowseDltData.py", "Browse/Search Observations"),
            Page("pages/Schema_Blame.py", "Schema Inspector"),
            Page("pages/debug_page.py","Debug Tools")]
