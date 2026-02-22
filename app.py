import streamlit as st
import tempfile
import os
import base64

from run_pipeline import run

st.set_page_config(
    page_title="Parts Extractor",
    page_icon="📄",
    layout="wide"
)

st.title("📄 Parts Extractor — PDF → Excel")

# ======================================================
# HELPER: PDF VIEWER (SCROLLABLE)
# ======================================================

import streamlit.components.v1 as components

def pdf_viewer(file_bytes: bytes, height: int = 900):
    """Chrome-safe scrollable PDF viewer"""
    b64 = base64.b64encode(file_bytes).decode()

    html = f"""
    <div style="height:{height}px; overflow:auto; border:1px solid #ccc;">
        <embed
            src="data:application/pdf;base64,{b64}"
            type="application/pdf"
            width="100%"
            height="100%"
        />
    </div>
    """

    components.html(html, height=height + 20, scrolling=True)

# ======================================================
# FILE UPLOAD
# ======================================================

uploaded_file = st.file_uploader(
    "Upload PDF Manual",
    type=["pdf"]
)

if uploaded_file is not None:
    file_bytes = uploaded_file.read()

    # Save to temp file for pipeline
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(file_bytes)
        pdf_path = tmp.name

    st.success("PDF uploaded successfully")

    # ==================================================
    # LAYOUT: TWO COLUMNS
    # ==================================================

    left_col, right_col = st.columns(2)

    # ------------------ INPUT PDF VIEW -----------------
    with left_col:
        st.subheader("📥 Input PDF Preview")
        pdf_viewer(file_bytes, height=900)

    # ==================================================
    # RUN EXTRACTION
    # ==================================================

    if st.button("▶ Run Extraction"):
        with st.spinner("Processing..."):
            output_xlsx, debug_pdf = run(pdf_path=pdf_path)

        st.success("Extraction complete")

        # ==============================================
        # DOWNLOAD OUTPUT EXCEL
        # ==============================================

        with open(output_xlsx, "rb") as f:
            st.download_button(
                label="⬇ Download Excel",
                data=f,
                file_name=os.path.basename(output_xlsx),
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

        # ==============================================
        # DEBUG PDF VIEW (RIGHT COLUMN)
        # ==============================================

        with right_col:
            st.subheader("🛠 Debug PDF Preview")

            if debug_pdf and os.path.exists(debug_pdf):
                with open(debug_pdf, "rb") as f:
                    debug_bytes = f.read()
                pdf_viewer(debug_bytes, height=900)

                # Download debug file
                st.download_button(
                    label="⬇ Download Debug PDF",
                    data=debug_bytes,
                    file_name=os.path.basename(debug_pdf),
                    mime="application/pdf"
                )
            else:
                st.info("No debug PDF generated.")

    # Cleanup temp file when app reruns
    try:
        os.unlink(pdf_path)
    except Exception:
        pass

