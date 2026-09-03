import base64

from discovery import extract_linkedin_job_urls
from discovery import BrowserSettings, LinkedInPublicJobsProvider


def test_extracts_and_canonicalizes_direct_variants():
    urls = extract_linkedin_job_urls([
        "https://www.linkedin.com/jobs/view/123456789/",
        "https://linkedin.com/jobs/view/123456789?trk=abc",
        "https://www.linkedin.com/jobs/view/987654321",
    ])
    assert urls == [
        "https://www.linkedin.com/jobs/view/123456789/",
        "https://www.linkedin.com/jobs/view/987654321/",
    ]


def test_extracts_bing_redirect_destination():
    destination = "https://www.linkedin.com/jobs/view/4456463987/?trk=bing"
    redirect = "https://www.bing.com/ck/a?u=a1" + base64.b64encode(destination.encode()).decode()
    assert extract_linkedin_job_urls([redirect]) == ["https://www.linkedin.com/jobs/view/4456463987/"]


def test_rejects_non_job_and_unrelated_urls():
    urls = extract_linkedin_job_urls([
        "https://www.linkedin.com/company/dexcom/",
        "https://www.linkedin.com/jobs/search/?keywords=Dexcom",
        "https://www.linkedin.com/in/someone/",
        "https://example.com/jobs/view/123456789/",
    ])
    assert urls == []


def test_rejects_observed_bing_redirect_to_non_linkedin_result():
    destination = "https://www.mountainproject.com/area/105891970/obed-clear-creek"
    redirect = "https://www.bing.com/ck/a?u=a1" + base64.b64encode(destination.encode()).decode()
    assert extract_linkedin_job_urls([redirect]) == []


def test_extracts_escaped_url_from_rendered_markup():
    markup = '<a href="https://www.linkedin.com/jobs/view/2233445566/?trk=foo&amp;ref=bar">job</a>'
    assert extract_linkedin_job_urls([markup]) == ["https://www.linkedin.com/jobs/view/2233445566/"]


def test_public_linkedin_filter_url_uses_requested_time_period():
    week = LinkedInPublicJobsProvider(BrowserSettings(), "7days")._url()
    day = LinkedInPublicJobsProvider(BrowserSettings(), "24hours")._url()
    assert "keywords=Dexcom" in week and "location=Worldwide" in week and "f_TPR=r604800" in week
    assert "f_TPR=r86400" in day
