import streamlit as st
import tempfile
import os

from run_pipeline import run

st.set_page_config(
    page_title="Parts",
    page_icon="📄",
    layout="wide"
)

st.title("📄 Parts Extractor — PDF → Excel")

# ======================================================
# FILE UPLOAD
# ======================================================

uploaded_file = st.file_uploader(
    "Upload PDF Manual",
    type=["pdf"]
)

# ======================================================
# METADATA INPUT (NEW SECTION)
# ======================================================

st.subheader("Project & Equipment Details (Optional)")

col1, col2 = st.columns(2)

vendor = col1.text_input("Vendor")import streamlit as st
import base64
import tempfile
import os
from PyPDF2 import PdfReader

# ======================================================
# OPTIONAL: your pipeline import
# Replace with your actual run() if needed
# ======================================================

def run_pipeline(pdf_path, pages=None):
    """
    DEMO pipeline.
    Replace this with your actual run() function.

    For testing, it just returns the same PDF as debug output.
    """

    debug_pdf_path = pdf_path  # pretend pipeline created debug file
    return debug_pdf_path


# ======================================================
# STREAMLIT CONFIG
# ======================================================

st.set_page_config(
    page_title="PDF Parts Extractor",
    page_icon="📄",
    layout="wide"
)

st.title("📄 PDF Viewer + Page Selection + Debug Viewer")


# ======================================================
# PDF VIEWER FUNCTION
# ======================================================

def show_pdf(pdf_bytes, height=850):

    base64_pdf = base64.b64encode(pdf_bytes).decode("utf-8")

    pdf_display = f"""
    <iframe
        src="data:application/pdf;base64,{base64_pdf}"
        width="100%"
        height="{height}px"
        style="border:none;">
    </iframe>
    """

    st.markdown(pdf_display, unsafe_allow_html=True)


# ======================================================
# FILE UPLOAD
# ======================================================

uploaded_file = st.file_uploader(
    "Upload PDF Manual",
    type=["pdf"]
)


# ======================================================
# MAIN LOGIC
# ======================================================

if uploaded_file is not None:

    pdf_bytes = uploaded_file.read()

    # Save uploaded PDF to temp file
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    temp_file.write(pdf_bytes)
    temp_file.close()

    pdf_path = temp_file.name

    # --------------------------------------------------
    # GET PAGE COUNT
    # --------------------------------------------------
    reader = PdfReader(pdf_path)
    total_pages = len(reader.pages)

    st.success(f"Total Pages: {total_pages}")

    # --------------------------------------------------
    # PAGE SELECTION
    # --------------------------------------------------
    page_options = list(range(1, total_pages + 1))

    selected_pages = st.multiselect(
        "Select pages to process (random allowed)",
        options=page_options,
        default=st.session_state.get("pages_to_process", [])
    )

    if st.button("Save Page List"):
        st.session_state["pages_to_process"] = selected_pages
        st.success("Page list saved!")

    st.write("📌 Selected Pages:",
             st.session_state.get("pages_to_process", []))

    # --------------------------------------------------
    # LAYOUT — PDF VIEWER
    # --------------------------------------------------
    left, right = st.columns([2, 1])

    with left:
        st.subheader("Uploaded PDF")
        show_pdf(pdf_bytes)

    with right:
        st.info("Scroll inside viewer to navigate pages")

    # --------------------------------------------------
    # RUN PIPELINE
    # --------------------------------------------------
    st.divider()

    if st.button("🚀 Run Processing"):

        pages = st.session_state.get("pages_to_process", None)

        debug_pdf_path = run_pipeline(
            pdf_path=pdf_path,
            pages=pages
        )

        st.session_state["debug_pdf_path"] = debug_pdf_path

        st.success("Processing complete!")

# ======================================================
# SHOW DEBUG PDF AFTER EXECUTION
# ======================================================

if "debug_pdf_path" in st.session_state:

    st.divider()
    st.subheader("🛠 Debug PDF")

    with open(st.session_state["debug_pdf_path"], "rb") as f:
        debug_bytes = f.read()

    show_pdf(debug_bytes)
model = col2.text_input("Model")

project = col1.text_input("Project")
subproject = col2.text_input("Sub Project")

equipment = st.text_input("Equipment Name")

# Convert empty strings → None
vendor = vendor.strip() or None
model = model.strip() or None
project = project.strip() or None
subproject = subproject.strip() or None
equipment = equipment.strip() or None


# ======================================================
# PAGE SELECTION MODE
# ======================================================

st.subheader("Page Selection")

mode = st.radio(
    "Choose mode",
    ["All pages", "Page range", "Specific pages"]
)

pages = None

# ---------- PAGE RANGE ----------
if mode == "Page range":

    col1, col2 = st.columns(2)

    start_page = col1.number_input(
        "Start Page",
        min_value=1,
        value=1
    )

    end_page = col2.number_input(
        "End Page",
        min_value=1,
        value=1
    )

    if start_page > end_page:
        st.error("Start page must be ≤ End page")
    else:
        pages = list(range(start_page, end_page + 1))

# ---------- SPECIFIC PAGES ----------
elif mode == "Specific pages":

    page_input = st.text_input(
        "Enter pages (comma-separated)",
        placeholder="e.g. 1,3,5,8,10"
    )

    if page_input:
        try:
            pages = sorted({
                int(p.strip())
                for p in page_input.split(",")
                if p.strip()
            })
        except ValueError:
            st.error("Invalid page numbers")

# ======================================================
# OPTIONS
# ======================================================

st.subheader("Options")

debug = st.checkbox(
    "Generate debug overlay PDF",
    value=False
)

# ======================================================
# RUN BUTTON
# ======================================================

if st.button("🚀 Run Extraction", use_container_width=True):

    if not uploaded_file:
        st.error("Please upload a PDF file")
        st.stop()

    # Save uploaded file temporarily
    # with tempfile.NamedTemporaryFile(
    #     delete=False,
    #     suffix=".pdf"
    # ) as tmp:

    #     tmp.write(uploaded_file.read())
    #     pdf_path = tmp.name
    # Create temp directory
    temp_dir = tempfile.gettempdir()
    
    # Use original filename
    original_name = uploaded_file.name
    
    pdf_path = os.path.join(temp_dir, original_name)
    
    with open(pdf_path, "wb") as f:
        f.write(uploaded_file.read())

    output_csv = pdf_path.replace(".pdf", ".csv")

    progress = st.progress(0)
    progress.progress(20)

    with st.spinner("Processing document..."):

        output_xlsx = run(
            pdf_path=pdf_path,
            output_csv=output_csv,
            vendor=vendor,
            model=model,
            project=project,
            subproject=subproject,
            equipment=equipment,
            debug=debug,
            pages=pages
        )

    progress.progress(100)

    st.success("Extraction completed successfully!")

    # ==================================================
    # DOWNLOAD OUTPUT
    # ==================================================

    with open(output_xlsx, "rb") as f:
        st.download_button(
            "⬇️ Download Excel Output",
            f,
            file_name=os.path.basename(output_xlsx),
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )

    # Optional debug PDF download
    if debug:
        debug_pdf = pdf_path.replace(".pdf", "_debug.pdf")

        if os.path.exists(debug_pdf):
            with open(debug_pdf, "rb") as f:
                st.download_button(
                    "⬇️ Download Debug Overlay PDF",
                    f,
                    file_name=os.path.basename(debug_pdf),
                    mime="application/pdf",
                    use_container_width=True
                )

