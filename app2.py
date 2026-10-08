import os
import re
import io
import json
import uuid
import hashlib
import datetime as dt
import random
from pathlib import Path

import streamlit as st
from PIL import Image, ExifTags

# Optional AI/TTS integrations. The app still runs in demo mode if these are
# not configured.
try:
    from google import genai
except Exception:
    genai = None

try:
    from gtts import gTTS
except Exception:
    gTTS = None


APP_NAME = "RoadGuard AI"
APP_VERSION = "1.0.0"
DEMO_NOTICE = "Prototype / Hacktoberfest demonstration — not an official Government of India portal"

st.set_page_config(
    page_title=f"{APP_NAME} | Citizen Infrastructure Portal",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ---------------------------------------------------------------------------
# SESSION STATE
# ---------------------------------------------------------------------------
DEFAULT_STATE = {
    "app_step": "form",
    "otp_code": None,
    "audit_data": {},
    "report_text": None,
    "complaint_id": None,
}
for key, value in DEFAULT_STATE.items():
    if key not in st.session_state:
        st.session_state[key] = value


# ---------------------------------------------------------------------------
# LIGHT / WHITE GOVERNMENT-STYLE UI
# ---------------------------------------------------------------------------
st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

:root { color-scheme: light; }

html, body, [data-testid="stAppViewContainer"], .stApp {
    background: #f7f9fc !important;
    color: #172033 !important;
    font-family: Inter, Arial, sans-serif !important;
}

[data-testid="stHeader"] {
    background: #ffffff !important;
    border-bottom: 1px solid #e5e7eb !important;
}

.block-container {
    max-width: 1250px !important;
    padding-top: 1.2rem !important;
    padding-bottom: 3rem !important;
}

[data-testid="stSidebar"] {
    background: #ffffff !important;
    border-right: 1px solid #e5e7eb !important;
}

[data-testid="stSidebarContent"] {
    padding-top: 1rem !important;
}

h1, h2, h3, h4, h5, h6, p, label, .stMarkdown {
    color: #172033 !important;
}

.gov-strip {
    height: 5px;
    border-radius: 5px 5px 0 0;
    background: linear-gradient(
        90deg,
        #ff9933 0 33.33%,
        #ffffff 33.33% 66.66%,
        #138808 66.66% 100%
    );
}

.gov-header {
    background: #ffffff;
    border: 1px solid #dfe5ee;
    border-top: none;
    border-radius: 0 0 14px 14px;
    padding: 18px 22px;
    box-shadow: 0 8px 28px rgba(15, 23, 42, 0.06);
    margin-bottom: 18px;
}

.gov-header-row {
    display: flex;
    align-items: center;
    gap: 16px;
}

.ashoka {
    width: 58px;
    height: 58px;
    border: 2px solid #1f3b63;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #1f3b63;
    font-size: 27px;
    font-weight: 800;
    flex: 0 0 auto;
}

.gov-kicker {
    color: #536174 !important;
    font-size: 12px;
    font-weight: 700;
    letter-spacing: .08em;
    text-transform: uppercase;
}

.gov-title {
    color: #102a43 !important;
    font-size: 25px;
    font-weight: 800;
    margin-top: 2px;
}

.gov-subtitle {
    color: #5b677a !important;
    font-size: 13px;
    margin-top: 3px;
}

.demo-banner {
    background: #fff8e8;
    border: 1px solid #f4d58a;
    color: #6b4b00 !important;
    padding: 10px 14px;
    border-radius: 9px;
    font-size: 12px;
    margin: 12px 0 20px;
}

.section-card {
    background: #ffffff;
    border: 1px solid #dfe5ee;
    border-radius: 14px;
    padding: 18px 20px;
    box-shadow: 0 5px 20px rgba(15, 23, 42, 0.04);
    margin-bottom: 16px;
}

.step-number {
    display: inline-flex;
    width: 29px;
    height: 29px;
    align-items: center;
    justify-content: center;
    border-radius: 50%;
    background: #123b69;
    color: #ffffff !important;
    font-weight: 800;
    margin-right: 7px;
}

.status-pill {
    display: inline-block;
    background: #ecfdf3;
    color: #137333 !important;
    border: 1px solid #b7ebc6;
    padding: 5px 10px;
    border-radius: 999px;
    font-size: 12px;
    font-weight: 700;
}

.stTextInput input, .stTextArea textarea, div[data-baseweb="select"] {
    background: #ffffff !important;
    color: #172033 !important;
    border: 1px solid #cbd5e1 !important;
    border-radius: 8px !important;
}

.stTextInput input:focus, .stTextArea textarea:focus {
    border-color: #1d5ea8 !important;
    box-shadow: 0 0 0 2px rgba(29, 94, 168, .12) !important;
}

div.stButton > button {
    border-radius: 8px !important;
    font-weight: 700 !important;
    border: 1px solid #b9c6d8 !important;
    background: #ffffff !important;
    color: #123b69 !important;
}

div.stButton > button[kind="primary"] {
    background: #123b69 !important;
    color: #ffffff !important;
    border-color: #123b69 !important;
}

div.stButton > button:hover {
    border-color: #123b69 !important;
}

.metric-card {
    background: #ffffff;
    border: 1px solid #dfe5ee;
    border-radius: 12px;
    padding: 12px 14px;
    text-align: center;
}

.footer {
    border-top: 1px solid #e2e8f0;
    margin-top: 28px;
    padding-top: 15px;
    color: #667085 !important;
    font-size: 11px;
    text-align: center;
}
</style>
""",
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------------
# DATA
# ---------------------------------------------------------------------------
INDIAN_STATES_DISTRICTS = {
    "Andaman and Nicobar Islands": ["Nicobar", "North and Middle Andaman", "South Andaman"],
    "Andhra Pradesh": ["Anantapur", "Chittoor", "East Godavari", "Guntur", "Krishna", "Kurnool", "Prakasam", "Srikakulam", "Visakhapatnam", "Vizianagaram", "West Godavari", "YSR Kadapa"],
    "Arunachal Pradesh": ["Changlang", "East Kameng", "East Siang", "Itanagar Capital Complex", "Lohit", "Papum Pare", "Tawang", "Tirap", "West Kameng"],
    "Assam": ["Barpeta", "Cachar", "Darrang", "Dhubri", "Dibrugarh", "Goalpara", "Golaghat", "Jorhat", "Kamrup", "Kamrup Metropolitan", "Karbi Anglong", "Karimganj", "Nagaon", "Sivasagar", "Sonitpur", "Tinsukia"],
    "Bihar": ["Araria", "Aurangabad", "Banka", "Begusarai", "Bhagalpur", "Bhojpur", "Gaya", "Gopalganj", "Katihar", "Madhubani", "Munger", "Muzaffarpur", "Nalanda", "Patna", "Purnia", "Rohtas", "Samastipur", "Saran", "Siwan", "Vaishali"],
    "Chandigarh": ["Chandigarh"],
    "Chhattisgarh": ["Bastar", "Bilaspur", "Durg", "Janjgir-Champa", "Korba", "Raigarh", "Raipur", "Rajnandgaon", "Surguja"],
    "Dadra and Nagar Haveli and Daman and Diu": ["Dadra and Nagar Haveli", "Daman", "Diu"],
    "Delhi": ["Central Delhi", "East Delhi", "New Delhi", "North Delhi", "North East Delhi", "North West Delhi", "Shahdara", "South Delhi", "South East Delhi", "South West Delhi", "West Delhi"],
    "Goa": ["North Goa", "South Goa"],
    "Gujarat": ["Ahmedabad", "Amreli", "Anand", "Banaskantha", "Bharuch", "Bhavnagar", "Dahod", "Gandhinagar", "Jamnagar", "Junagadh", "Kheda", "Kutch", "Mehsana", "Patan", "Rajkot", "Surat", "Vadodara", "Valsad"],
    "Haryana": ["Ambala", "Bhiwani", "Faridabad", "Gurugram", "Hisar", "Jhajjar", "Jind", "Karnal", "Kurukshetra", "Panipat", "Rohtak", "Sirsa", "Sonipat", "Yamunanagar"],
    "Himachal Pradesh": ["Bilaspur", "Chamba", "Hamirpur", "Kangra", "Kullu", "Mandi", "Shimla", "Sirmaur", "Solan", "Una"],
    "Jammu and Kashmir": ["Anantnag", "Baramulla", "Budgam", "Doda", "Jammu", "Kathua", "Kupwara", "Poonch", "Pulwama", "Rajouri", "Srinagar", "Udhampur"],
    "Jharkhand": ["Bokaro", "Dhanbad", "Dumka", "East Singhbhum", "Giridih", "Hazaribagh", "Deoghar", "Palamu", "Ranchi", "West Singhbhum"],
    "Karnataka": ["Bagalkot", "Ballari", "Belagavi", "Bengaluru Rural", "Bengaluru Urban", "Bidar", "Chikkamagaluru", "Dakshina Kannada", "Davanagere", "Dharwad", "Hassan", "Kalaburagi", "Kodagu", "Kolar", "Mandya", "Mysuru", "Raichur", "Shivamogga", "Tumakuru", "Udupi", "Uttara Kannada", "Vijayapura"],
    "Kerala": ["Alappuzha", "Ernakulam", "Idukki", "Kannur", "Kasaragod", "Kollam", "Kottayam", "Kozhikode", "Malappuram", "Palakkad", "Pathanamthitta", "Thiruvananthapuram", "Thrissur", "Wayanad"],
    "Ladakh": ["Kargil", "Leh"],
    "Lakshadweep": ["Lakshadweep"],
    "Madhya Pradesh": ["Bhopal", "Chhindwara", "Gwalior", "Indore", "Jabalpur", "Mandsaur", "Morena", "Rewa", "Sagar", "Satna", "Ujjain", "Vidisha"],
    "Maharashtra": ["Ahmednagar", "Akola", "Amravati", "Chhatrapati Sambhajinagar", "Beed", "Chandrapur", "Dhule", "Jalgaon", "Kolhapur", "Latur", "Mumbai City", "Mumbai Suburban", "Nagpur", "Nanded", "Nashik", "Palghar", "Pune", "Raigad", "Ratnagiri", "Sangli", "Satara", "Solapur", "Thane"],
    "Manipur": ["Bishnupur", "Churachandpur", "Imphal East", "Imphal West", "Senapati", "Thoubal", "Ukhrul"],
    "Meghalaya": ["East Garo Hills", "East Jaintia Hills", "East Khasi Hills", "Ri-Bhoi", "West Garo Hills", "West Khasi Hills"],
    "Mizoram": ["Aizawl", "Champhai", "Kolasib", "Lunglei", "Serchhip"],
    "Nagaland": ["Dimapur", "Kohima", "Mokokchung", "Mon", "Tuensang", "Wokha", "Zunheboto"],
    "Odisha": ["Angul", "Balangir", "Balasore", "Bargarh", "Bhadrak", "Cuttack", "Dhenkanal", "Gajapati", "Ganjam", "Jagatsinghpur", "Jajpur", "Jharsuguda", "Kalahandi", "Kandhamal", "Kendrapara", "Kendujhar", "Khordha", "Koraput", "Mayurbhanj", "Nabarangpur", "Nayagarh", "Puri", "Rayagada", "Sambalpur", "Subarnapur", "Sundargarh"],
    "Puducherry": ["Karaikal", "Mahe", "Puducherry", "Yanam"],
    "Punjab": ["Amritsar", "Bathinda", "Faridkot", "Fatehgarh Sahib", "Ferozepur", "Gurdaspur", "Hoshiarpur", "Jalandhar", "Kapurthala", "Ludhiana", "Moga", "Patiala", "Rupnagar", "SAS Nagar", "Sangrur"],
    "Rajasthan": ["Ajmer", "Alwar", "Banswara", "Barmer", "Bharatpur", "Bhilwara", "Bikaner", "Chittorgarh", "Churu", "Jaipur", "Jaisalmer", "Jodhpur", "Kota", "Nagaur", "Pali", "Sikar", "Sri Ganganagar", "Udaipur"],
    "Sikkim": ["East Sikkim", "North Sikkim", "South Sikkim", "West Sikkim"],
    "Tamil Nadu": ["Chennai", "Coimbatore", "Cuddalore", "Dharmapuri", "Dindigul", "Erode", "Kanchipuram", "Kanyakumari", "Karur", "Madurai", "Nagapattinam", "Namakkal", "Nilgiris", "Pudukkottai", "Ramanathapuram", "Salem", "Sivaganga", "Thanjavur", "Theni", "Thoothukudi", "Tiruchirappalli", "Tirunelveli", "Tiruppur", "Vellore", "Viluppuram"],
    "Telangana": ["Bhadradri Kothagudem", "Hyderabad", "Jagtial", "Karimnagar", "Khammam", "Mahabubnagar", "Mancherial", "Medak", "Medchal-Malkajgiri", "Nalgonda", "Nizamabad", "Peddapalli", "Rangareddy", "Sangareddy", "Siddipet", "Suryapet", "Warangal"],
    "Tripura": ["Dhalai", "Gomati", "North Tripura", "South Tripura", "Unakoti", "West Tripura"],
    "Uttar Pradesh": ["Agra", "Aligarh", "Ambedkar Nagar", "Azamgarh", "Bareilly", "Bulandshahr", "Etawah", "Farrukhabad", "Ghaziabad", "Gonda", "Gorakhpur", "Jalaun", "Jaunpur", "Jhansi", "Kanpur Nagar", "Lakhimpur Kheri", "Lucknow", "Mathura", "Meerut", "Mirzapur", "Moradabad", "Muzaffarnagar", "Prayagraj", "Rae Bareli", "Saharanpur", "Shahjahanpur", "Sitapur", "Varanasi"],
    "Uttarakhand": ["Almora", "Bageshwar", "Chamoli", "Dehradun", "Haridwar", "Nainital", "Pauri Garhwal", "Pithoragarh", "Rudraprayag", "Tehri Garhwal", "Udham Singh Nagar", "Uttarkashi"],
    "West Bengal": ["Bankura", "Birbhum", "Cooch Behar", "Darjeeling", "Hooghly", "Howrah", "Jalpaiguri", "Kolkata", "Malda", "Murshidabad", "Nadia", "North 24 Parganas", "Paschim Bardhaman", "Paschim Medinipur", "Purba Bardhaman", "Purba Medinipur", "Purulia", "South 24 Parganas", "Uttar Dinajpur"],
}

TARGET_AUTHORITIES = [
    "District Magistrate (DM) / Collector Office",
    "Executive Engineer (PWD Roads & Bridges)",
    "State Highway / NHAI Regional Officer",
    "Chief Minister Grievance Cell (CMO)",
]

LANGUAGES = ["English", "Hindi", "Odia"]
LANG_CODE_MAP = {"English": "en", "Hindi": "hi", "Odia": "or"}

# Keep the original required detail fields unchanged.
REQUIRED_FIELDS = [
    "Full Name",
    "Email Address",
    "Mobile Number",
    "Gender",
    "State",
    "District",
    "City / Town",
    "Area / Ward / Street",
    "Postal Pin Code",
    "Photo",
    "Problem Description",
]


# ---------------------------------------------------------------------------
# UTILITIES
# ---------------------------------------------------------------------------
class AuditEngine:
    FORBIDDEN_WORDS = [
        "gali", "madarchod", "bhosdike", "chutiya", "sala",
        "maghia", "randi", "harami", "fuck", "shit", "bastard",
    ]

    @staticmethod
    def calculate_image_hash(image_bytes: bytes) -> str:
        return hashlib.sha256(image_bytes).hexdigest()

    @staticmethod
    def extract_exif_data(img: Image.Image) -> dict:
        metadata = {}
        try:
            exif_data = img.getexif()
            if exif_data:
                for tag_id, value in exif_data.items():
                    tag = ExifTags.TAGS.get(tag_id, tag_id)
                    if tag in ["DateTimeOriginal", "Make", "Model", "GPSInfo"]:
                        metadata[str(tag)] = str(value)
        except Exception:
            pass
        return metadata

    @classmethod
    def sanitize_input(cls, text: str) -> bool:
        if not text:
            return False
        lowered = text.lower()
        return any(re.search(rf"\b{re.escape(word)}\b", lowered) for word in cls.FORBIDDEN_WORDS)


def now_string():
    return dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def make_complaint_id():
    return f"RG-{dt.datetime.now():%Y%m%d}-{uuid.uuid4().hex[:6].upper()}"


def get_api_key():
    # Never hard-code API keys into source code.
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if key:
        return key
    try:
        return st.secrets.get("GEMINI_API_KEY", "")
    except Exception:
        return ""


def generate_demo_report(data, img_hash, exif_info, timestamp):
    location = data["full_location"]
    authority = data["target_authority"]
    description = data["voice_statement"]
    return f"""
## Preliminary Infrastructure Audit

**Complaint ID:** {data["complaint_id"]}  
**Audit timestamp:** {timestamp}  
**Evidence SHA-256:** `{img_hash}`  
**Evidence metadata detected:** {"Yes" if exif_info else "No / unavailable"}

### 1. Citizen statement
{description}

### 2. Field evidence review
The uploaded image has been accepted by the portal as infrastructure evidence. A human authority should verify the physical condition, exact location, severity, ownership of the road, and applicable engineering standards before taking administrative action.

### 3. Suggested inspection points
- Road-surface damage and pothole extent
- Drainage / waterlogging conditions
- Surface and sub-base condition
- Safety risk to pedestrians and vehicles
- Need for site inspection and measurement

### 4. Administrative routing
**Suggested authority:** {authority}  
**Reported location:** {location}

### 5. Requested action
Please conduct a field inspection and take appropriate action under the applicable local road-maintenance and public-works procedures.

> This is a prototype-generated draft. It is not a legal finding, engineering certification, or official government order.
""".strip()


def generate_ai_report(data, img, img_hash, exif_info, timestamp):
    api_key = get_api_key()
    if not api_key or genai is None:
        return generate_demo_report(data, img_hash, exif_info, timestamp)

    prompt = f"""
You are assisting a civic infrastructure reporting prototype.

Analyze the uploaded image for visible road/civil-infrastructure issues such as potholes,
asphalt damage, cracks, drainage problems, or related defects.

Do not claim legal violations as established facts. Clearly distinguish visible evidence,
possible engineering concerns, and items requiring official site verification.

Prepare a formal draft in {data["selected_language"]} with:
1. Forensic summary: SHA-256, timestamp, metadata availability.
2. Visible infrastructure observations.
3. Engineering inspection points.
4. Administrative routing suggestion.
5. Formal citizen complaint draft.

Location: {data["full_location"]}
Authority: {data["target_authority"]}
Complainant: {data["user_name"]}
Citizen statement: {data["voice_statement"]}
Evidence SHA-256: {img_hash}
Timestamp: {timestamp}

End with a clear statement that the result is a prototype draft and not an official
government decision or legal/engineering certification.
"""

    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[prompt, img],
    )
    return response.text


# ---------------------------------------------------------------------------
# COMMON HEADER / FOOTER
# ---------------------------------------------------------------------------
def render_header():
    st.markdown(
        """
<div class="gov-strip"></div>
<div class="gov-header">
  <div class="gov-header-row">
    <div class="ashoka">✦</div>
    <div>
      <div class="gov-kicker">Citizen Infrastructure Services</div>
      <div class="gov-title">RoadGuard AI — Citizen Audit & Compliance Portal</div>
      <div class="gov-subtitle">Report road and public-infrastructure issues with evidence and structured administrative routing.</div>
    </div>
  </div>
</div>
<div class="demo-banner">
  <strong>DEMO / HACKTOBERFEST BUILD:</strong> This interface is designed in a Government-service style,
  but it is <strong>not an official Government of India website</strong> and does not directly submit complaints
  to a government department.
</div>
""",
        unsafe_allow_html=True,
    )


def render_footer():
    st.markdown(
        """
<div class="footer">
RoadGuard AI v1.0.0 · Civic technology prototype · No official government affiliation claimed<br>
Evidence processing is intended for demonstration and should be reviewed by an authorized human before real-world use.
</div>
""",
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# FORM
# ---------------------------------------------------------------------------
def render_main_form():
    render_header()

    with st.sidebar:
        st.markdown("## Help & Restrictions")
        with st.expander("View Guidelines & Penalties"):
            st.markdown(
                """
- Use clear, factual language.
- Upload evidence that you are permitted to share.
- Do not submit intentionally false or abusive complaints.
- A prototype report is not an official legal or engineering decision.
"""
            )

        st.markdown("---")
        st.markdown("## Terms & Privacy Policy")
        with st.expander("View Terms & Policies"):
            st.markdown(
                """
- Uploaded evidence is processed to create the demonstration audit report.
- The prototype does not claim direct government submission.
- For a production deployment, add authentication, encryption, retention controls,
  audit logging, official API integrations, and a published privacy policy.
"""
            )

        st.markdown("---")
        st.markdown("## Complainant & Jurisdiction")

        user_name = st.text_input("Full Name *", placeholder="e.g., Jagalinki Sai Kiran")
        user_email = st.text_input("Email Address *", placeholder="e.g., user@domain.com")
        user_phone = st.text_input("Mobile Number *", placeholder="e.g., 9876543210")

        gender_options = ["Select Gender...", "Male", "Female", "Other", "Prefer not to say"]
        selected_gender = st.selectbox("Gender *", gender_options)

        state_list = ["Select State..."] + sorted(INDIAN_STATES_DISTRICTS.keys())
        selected_state = st.selectbox("State *", state_list)

        district_options = ["Select District..."]
        if selected_state != "Select State..." and selected_state in INDIAN_STATES_DISTRICTS:
            district_options += sorted(INDIAN_STATES_DISTRICTS[selected_state])
        district_options.append("Other / Custom District")
        selected_district = st.selectbox("District *", district_options)

        custom_district = ""
        if selected_district == "Other / Custom District":
            custom_district = st.text_input("Enter Custom District Name *", placeholder="Type district name")

        city_town = st.text_input("City / Town *", placeholder="e.g., Brahmapur")
        village_area = st.text_input("Area / Ward / Street *", placeholder="e.g., Ambapua Main Road")
        pincode = st.text_input("Postal Pin Code *", placeholder="e.g., 760001")

        st.markdown("---")
        target_authority = st.selectbox("Target Authority", TARGET_AUTHORITIES)

        selected_language = st.selectbox("Report & Audio Language", LANGUAGES)

        # API key field intentionally omitted from the UI: use environment
        # variable GEMINI_API_KEY or .streamlit/secrets.toml instead.

    left, right = st.columns([1, 1], gap="large")

    with left:
        st.markdown(
            '<div class="section-card"><h3><span class="step-number">1</span>Upload Field Evidence *</h3>',
            unsafe_allow_html=True,
        )
        upload_mode = st.radio(
            "Source Mode",
            ["Upload Image File", "Live Camera Capture"],
            horizontal=True,
        )

        uploaded_file = None
        if upload_mode == "Upload Image File":
            uploaded_file = st.file_uploader(
                "Upload Infrastructure Evidence (JPG/PNG)",
                type=["jpg", "jpeg", "png"],
            )
        else:
            uploaded_file = st.camera_input("Capture Live Field Evidence")
        st.markdown("</div>", unsafe_allow_html=True)

    with right:
        st.markdown(
            '<div class="section-card"><h3><span class="step-number">2</span>Problem Description *</h3>',
            unsafe_allow_html=True,
        )
        voice_statement = st.text_area(
            "Detailed Citizen Statement / Issue Description:",
            height=190,
            placeholder="Describe structural failure, asphalt peeling, potholes, or drainage issues...",
        )

        is_slang_detected = AuditEngine.sanitize_input(voice_statement)
        if is_slang_detected:
            st.error("Abuse filter triggered. Please use official, factual language.")
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown(
        """
<div class="section-card">
<strong>Submission requirements</strong><br>
All required identity, jurisdiction, evidence, and description fields must be completed before OTP verification.
</div>
""",
        unsafe_allow_html=True,
    )

    if st.button("Proceed to Secure OTP Verification", type="primary", use_container_width=True):
        final_district = custom_district if selected_district == "Other / Custom District" else selected_district

        missing = (
            not user_name.strip()
            or not user_email.strip()
            or not user_phone.strip()
            or selected_gender == "Select Gender..."
            or selected_state == "Select State..."
            or final_district in ["Select District...", ""]
            or not city_town.strip()
            or not village_area.strip()
            or not pincode.strip()
            or not voice_statement.strip()
            or uploaded_file is None
        )

        if missing:
            st.error(
                "Please fill all required fields! (Name, Email, Phone, Gender, State, District, City, Area, Pincode, Photo & Description are mandatory.)"
            )
            return

        if is_slang_detected:
            st.error("Action aborted. Please remove inappropriate language from your statement.")
            return

        if not re.fullmatch(r"\d{10}", re.sub(r"\D", "", user_phone)):
            st.error("Please enter a valid 10-digit mobile number.")
            return

        if not re.fullmatch(r"\d{6}", pincode.strip()):
            st.error("Please enter a valid 6-digit Postal Pin Code.")
            return

        try:
            image_bytes = uploaded_file.getvalue()
            img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
            img.load()
        except Exception:
            st.error("The uploaded file could not be read as a valid image.")
            return

        final_phone = re.sub(r"\D", "", user_phone)
        complaint_id = make_complaint_id()

        st.session_state["audit_data"] = {
            "user_name": user_name.strip(),
            "user_email": user_email.strip(),
            "user_phone": final_phone,
            "user_gender": selected_gender,
            "full_location": f"{village_area.strip()}, {city_town.strip()}, {final_district}, {selected_state} - {pincode.strip()}",
            "target_authority": target_authority,
            "selected_language": selected_language,
            "lang_code": LANG_CODE_MAP[selected_language],
            "voice_statement": voice_statement.strip(),
            "image_bytes": image_bytes,
            "image_obj": img,
            "upload_mode": upload_mode,
            "complaint_id": complaint_id,
        }

        # Demo OTP: shown on-screen rather than sent to a real telecom service.
        st.session_state["otp_code"] = str(random.randint(1000, 9999))
        st.session_state["app_step"] = "otp"
        st.rerun()


# ---------------------------------------------------------------------------
# OTP
# ---------------------------------------------------------------------------
def render_otp_verification_page():
    render_header()

    data = st.session_state["audit_data"]
    phone = data.get("user_phone", "")
    real_otp = st.session_state["otp_code"]

    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown("## Secure Mobile OTP Verification")
    st.write("Verify the mobile number before the prototype creates the administrative draft.")
    st.info(
        f"DEMO MODE: OTP for {phone} is **{real_otp}**. "
        "In production, replace this with an approved SMS/OTP provider."
    )

    entered_otp = st.text_input("Enter 4-Digit OTP Code *", max_chars=4)

    c1, c2 = st.columns(2)
    with c1:
        if st.button("Back to Form", use_container_width=True):
            st.session_state["app_step"] = "form"
            st.rerun()

    with c2:
        if st.button("Verify OTP & Prepare Report", type="primary", use_container_width=True):
            if entered_otp.strip() == real_otp:
                st.session_state["app_step"] = "success"
                st.rerun()
            else:
                st.error("Invalid OTP. Please enter the 4-digit demo OTP shown above.")

    st.markdown("</div>", unsafe_allow_html=True)
    render_footer()


# ---------------------------------------------------------------------------
# SUCCESS / REPORT
# ---------------------------------------------------------------------------
def render_success_page():
    render_header()

    data = st.session_state["audit_data"]
    img_hash = AuditEngine.calculate_image_hash(data["image_bytes"])
    exif_info = AuditEngine.extract_exif_data(data["image_obj"])
    timestamp = now_string()

    st.markdown(
        f"""
<div class="section-card">
<h2>Administrative Dispatch Preview</h2>
<span class="status-pill">OTP VERIFIED · DRAFT READY</span>
<p><strong>Complaint ID:</strong> {data["complaint_id"]}</p>
<p><strong>Target Authority:</strong> {data["target_authority"]}</p>
</div>
""",
        unsafe_allow_html=True,
    )

    st.image(data["image_obj"], caption="Submitted field evidence", use_container_width=True)

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Evidence Integrity", "Verified")
    with c2:
        st.metric("SHA-256", f"{img_hash[:14]}…")
    with c3:
        st.metric("Metadata", "Detected" if exif_info else "Unavailable")

    with st.expander("View evidence metadata"):
        st.json(exif_info if exif_info else {"status": "No selected EXIF metadata available"})

    if st.session_state.get("report_text") is None:
        with st.spinner("Preparing infrastructure audit report…"):
            try:
                st.session_state["report_text"] = generate_ai_report(
                    data, data["image_obj"], img_hash, exif_info, timestamp
                )
            except Exception as err:
                # Never expose credentials or full provider errors to the user.
                st.session_state["report_text"] = generate_demo_report(
                    data, img_hash, exif_info, timestamp
                )
                st.warning(
                    "AI provider unavailable, so the portal created a safe local demonstration report instead."
                )

    report_text = st.session_state["report_text"]

    st.markdown("---")
    st.markdown(f"### Formal Audit Report & Administrative Complaint ({data['selected_language']})")
    st.markdown(report_text)

    # Downloadable text package.
    package = {
        "application": APP_NAME,
        "version": APP_VERSION,
        "demo_status": True,
        "complaint_id": data["complaint_id"],
        "timestamp": timestamp,
        "complainant": {
            "name": data["user_name"],
            "email": data["user_email"],
            "phone": data["user_phone"],
            "gender": data["user_gender"],
        },
        "location": data["full_location"],
        "target_authority": data["target_authority"],
        "language": data["selected_language"],
        "citizen_statement": data["voice_statement"],
        "evidence_sha256": img_hash,
        "report": report_text,
    }

    st.download_button(
        "Download Complaint JSON Package",
        data=json.dumps(package, indent=2, ensure_ascii=False),
        file_name=f"{data['complaint_id']}.json",
        mime="application/json",
        use_container_width=True,
    )

    if gTTS is not None and report_text:
        if st.button("Generate Audio Briefing"):
            try:
                audio_path = Path(f"{data['complaint_id']}_audio.mp3")
                gTTS(
                    text=report_text[:1200].replace("*", "").replace("#", ""),
                    lang=data["lang_code"],
                ).save(audio_path)
                st.audio(str(audio_path), format="audio/mp3")
            except Exception:
                st.info("Audio generation is unavailable in this environment.")

    st.success(
        "Prototype package prepared successfully. A real deployment would now hand the verified package to an authenticated government API or authorized case-management system."
    )

    if st.button("File Another Audit Report"):
        for key, value in DEFAULT_STATE.items():
            st.session_state[key] = value
        st.rerun()

    render_footer()


# ---------------------------------------------------------------------------
# ROUTER
# ---------------------------------------------------------------------------
if st.session_state["app_step"] == "form":
    render_main_form()
elif st.session_state["app_step"] == "otp":
    render_otp_verification_page()
elif st.session_state["app_step"] == "success":
    render_success_page()
