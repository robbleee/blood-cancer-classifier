import streamlit as st
import bcrypt
import json
from openai import OpenAI
import uuid
import time
from streamlit_cookies_manager import EncryptedCookieManager

# Example imports for your parsers/classifiers/reviewers
from parsers.aml_parser import parse_genetics_report_aml
from parsers.aml_response_parser import parse_aml_response_report
from parsers.mds_parser import parse_genetics_report_mds
from classifiers.aml_classifier import classify_AML_WHO2022, classify_AML_ICC2022
from classifiers.aml_response_classifier import classify_AML_Response_ELN2022
from classifiers.mds_classifier import classify_MDS_WHO2022, classify_MDS_ICC2022
from reviewers.aml_reviewer import get_gpt4_review_aml
from reviewers.mds_reviewer import get_gpt4_review_mds

##############################
# PAGE CONFIG
##############################
st.set_page_config(page_title="Haematologic Classification", layout="wide")


##############################
# INITIALISE COOKIES
##############################
# Pull it as a string from st.secrets
password_str = st.secrets["general"]["cookie_password"]  # This is a plain string

# Pass the string directly to EncryptedCookieManager
cookies = EncryptedCookieManager(
    prefix="my_app_",
    password=password_str  # DO NOT encode it here
)

# This must be called after you define cookies but before using them
if not cookies.ready():
    st.stop()


if 'authenticated' not in st.session_state:
    st.session_state['authenticated'] = False
    st.session_state['username'] = ''

##############################
# AUTH FUNCTIONS
##############################
def verify_password(stored_password: str, provided_password: str) -> bool:
    return bcrypt.checkpw(provided_password.encode('utf-8'), stored_password.encode('utf-8'))

def authenticate_user(username: str, password: str) -> bool:
    users = st.secrets["auth"]["users"]
    for user in users:
        if user["username"] == username:
            return verify_password(user["hashed_password"], password)
    return False

def login_user(username: str):
    """
    Logs in a user by generating a random session ID 
    and saving it into the encrypted cookie and st.session_state.
    """
    session_id = str(uuid.uuid4())
    cookies["session_id"] = session_id
    cookies["username"] = username

    st.session_state['authenticated'] = True
    st.session_state['username'] = username

def logout_user():
    """
    Logs out the current user by removing the session cookie and 
    clearing session_state.
    """
    if "session_id" in cookies:
        del cookies["session_id"]
    if "username" in cookies:
        del cookies["username"]

    st.session_state['authenticated'] = False
    st.session_state['username'] = ''

def is_user_logged_in() -> bool:
    """
    Checks if a valid session exists in the cookies. 
    If found, sets session_state accordingly and returns True.
    Otherwise, returns False.
    """
    session_id = cookies.get("session_id")
    username = cookies.get("username")
    if session_id and username:
        # Optionally validate session_id server-side if you wish
        st.session_state['authenticated'] = True
        st.session_state['username'] = username
        return True
    return False

def login_logout():
    """
    Main function to handle login/logout in your sidebar (or anywhere).
    Checks if a session cookie is set. If so, display a logout button;
    otherwise display a login form.
    """
    if is_user_logged_in():
        st.sidebar.markdown(f"### Logged in as **{st.session_state['username']}**")
        if st.sidebar.button("Logout"):
            logout_user()
            st.sidebar.success("Logged out successfully!")
    else:
        st.sidebar.header("Login for AI Features")
        username = st.sidebar.text_input("Username")
        password = st.sidebar.text_input("Password", type="password")
        if st.sidebar.button("Login"):
            if authenticate_user(username, password):
                login_user(username)
                st.sidebar.success("Logged in successfully!")
            else:
                st.sidebar.error("Invalid username or password")


login_logout()


##############################
# HELPER: Build Compact Manual AML Data
##############################
def build_manual_aml_data() -> dict:
    """
    Displays a more compact Streamlit form that captures all AML fields
    matching the parse_genetics_report_aml schema.
    Returns a dictionary that can be fed to the AML classifiers.
    """

    st.markdown("### Manual AML Data Entry")

    # 1) Blasts Percentage
    st.markdown("**Blasts Percentage**")
    blasts = st.number_input("Blasts (%)", min_value=0.0, max_value=100.0, value=0.0)

    # 2) AML-defining Recurrent Genetic Abnormalities in 2 columns
    st.markdown("#### AML-defining Recurrent Genetic Abnormalities")
    c1, c2 = st.columns(2)
    with c1:
        npm1 = st.checkbox("NPM1 mutation")
        runx1_runx1t1 = st.checkbox("RUNX1::RUNX1T1 fusion")
        cbfb_myh11 = st.checkbox("CBFB::MYH11 fusion")
        dek_nup214 = st.checkbox("DEK::NUP214 fusion")
        rbm15_mrtfa = st.checkbox("RBM15::MRTFA fusion")

    with c2:
        mllt3_kmt2a = st.checkbox("MLLT3::KMT2A fusion")
        kmt2a = st.checkbox("KMT2A rearrangement (other)")
        mecom = st.checkbox("MECOM rearrangement")
        nup98 = st.checkbox("NUP98 rearrangement")
        cebpa = st.checkbox("CEBPA mutation")

    # Additional row for leftover items
    c3, c4 = st.columns(2)
    with c3:
        bzip = st.checkbox("CEBPA bZIP mutation")
    with c4:
        bcr_abl1 = st.checkbox("BCR::ABL1 fusion")

    # 3) Biallelic TP53 mutation
    st.markdown("#### Biallelic TP53 Mutation")
    tp1, tp2, tp3 = st.columns(3)
    with tp1:
        two_tp53 = st.checkbox("2 x TP53 mutations")
    with tp2:
        one_tp53_del17p = st.checkbox("1 x TP53 + del(17p)")
    with tp3:
        one_tp53_loh = st.checkbox("1 x TP53 + LOH")

    # Use expanders for MDS-related fields to shorten the page
    st.markdown("#### MDS Related Flags")
    with st.expander("MDS-related Mutations"):
        col_a, col_b = st.columns(2)
        with col_a:
            asxl1 = st.checkbox("ASXL1")
            bcor = st.checkbox("BCOR")
            ezh2 = st.checkbox("EZH2")
            runx1_mds = st.checkbox("RUNX1 (MDS-related)")
            sf3b1 = st.checkbox("SF3B1")
        with col_b:
            srsf2 = st.checkbox("SRSF2")
            stag2 = st.checkbox("STAG2")
            u2af1 = st.checkbox("U2AF1")
            zrsr2 = st.checkbox("ZRSR2")

    with st.expander("MDS-related Cytogenetics"):
        c_left, c_right = st.columns(2)
        with c_left:
            complex_kary = st.checkbox("Complex karyotype")
            del_5q = st.checkbox("del(5q)")
            t_5q = st.checkbox("t(5q)")
            add_5q = st.checkbox("add(5q)")
            minus7 = st.checkbox("-7")
            del_7q = st.checkbox("del(7q)")
            plus8 = st.checkbox("+8")
        with c_right:
            del_11q = st.checkbox("del(11q)")
            del_12p = st.checkbox("del(12p)")
            t_12p = st.checkbox("t(12p)")
            add_12p = st.checkbox("add(12p)")
            minus13 = st.checkbox("-13")
            i_17q = st.checkbox("i(17q)")
            minus17 = st.checkbox("-17")
            add_17p = st.checkbox("add(17p)")
            del_17p = st.checkbox("del(17p)")
            del_20q = st.checkbox("del(20q)")
            idic_x_q13 = st.checkbox("idic_X_q13")

    # AML Differentiation
    st.markdown("#### AML Differentiation")
    aml_diff = st.text_input("e.g. 'FAB M3', 'M4', 'WHO AML with myelodysplasia-related changes'", value="")

    # 7) Qualifiers
    st.markdown("#### Qualifiers")
    qc1, qc2 = st.columns(2)
    with qc1:
        prev_mds_3mo = st.checkbox("Previous MDS diagnosed >3 months ago")
        prev_mds_mpn_3mo = st.checkbox("Previous MDS/MPN diagnosed >3 months ago")

    with qc2:
        prev_cytotx = st.checkbox("Previous cytotoxic therapy?")
        germ_variant = st.text_input("Predisposing germline variant (if any)", value="None")

    # Build dictionary
    manual_data = {
        "blasts_percentage": blasts,
        "AML_defining_recurrent_genetic_abnormalities": {
            "NPM1": npm1,
            "RUNX1::RUNX1T1": runx1_runx1t1,
            "CBFB::MYH11": cbfb_myh11,
            "DEK::NUP214": dek_nup214,
            "RBM15::MRTFA": rbm15_mrtfa,
            "MLLT3::KMT2A": mllt3_kmt2a,
            "KMT2A": kmt2a,
            "MECOM": mecom,
            "NUP98": nup98,
            "CEBPA": cebpa,
            "bZIP": bzip,
            "BCR::ABL1": bcr_abl1
        },
        "Biallelic_TP53_mutation": {
            "2_x_TP53_mutations": two_tp53,
            "1_x_TP53_mutation_del_17p": one_tp53_del17p,
            "1_x_TP53_mutation_LOH": one_tp53_loh
        },
        "MDS_related_mutation": {
            "ASXL1": asxl1,
            "BCOR": bcor,
            "EZH2": ezh2,
            "RUNX1": runx1_mds,
            "SF3B1": sf3b1,
            "SRSF2": srsf2,
            "STAG2": stag2,
            "U2AF1": u2af1,
            "ZRSR2": zrsr2
        },
        "MDS_related_cytogenetics": {
            "Complex_karyotype": complex_kary,
            "del_5q": del_5q,
            "t_5q": t_5q,
            "add_5q": add_5q,
            "-7": minus7,
            "del_7q": del_7q,
            "+8": plus8,
            "del_11q": del_11q,
            "del_12p": del_12p,
            "t_12p": t_12p,
            "add_12p": add_12p,
            "-13": minus13,
            "i_17q": i_17q,
            "-17": minus17,
            "add_17p": add_17p,
            "del_17p": del_17p,
            "del_20q": del_20q,
            "idic_X_q13": idic_x_q13
        },
        "AML_differentiation": aml_diff.strip() if aml_diff.strip() else None,
        "qualifiers": {
            "previous_MDS_diagnosed_over_3_months_ago": prev_mds_3mo,
            "previous_MDS/MPN_diagnosed_over_3_months_ago": prev_mds_mpn_3mo,
            "previous_cytotoxic_therapy": prev_cytotx,
            "predisposing_germline_variant": germ_variant.strip() if germ_variant.strip() else "None"
        }
    }

    return manual_data


##############################
# HELPER: Build Manual MDS Data (Optional: Make it compact similarly)
##############################
def build_manual_mds_data() -> dict:
    """
    Displays a compact Streamlit form for MDS fields
    matching parse_genetics_report_mds schema.
    """

    st.markdown("### Manual MDS Data Entry (Compact)")

    # row for blasts, fibrotic, hypoplasia
    c1, c2, c3 = st.columns(3)
    with c1:
        blasts = st.number_input("Blasts (%)", min_value=0.0, max_value=100.0, value=0.0)
    with c2:
        fibrotic = st.checkbox("Fibrotic marrow?")
    with c3:
        hypoplasia = st.checkbox("Hypoplastic MDS?")

    # Dysplastic lineages
    dys_lineages = st.number_input("Number of Dysplastic Lineages (0-3)", min_value=0, max_value=3, value=0)

    st.markdown("#### Biallelic TP53 Mutation")
    ctp1, ctp2, ctp3 = st.columns(3)
    with ctp1:
        tp53_2 = st.checkbox("2 x TP53 mutations")
    with ctp2:
        tp53_17p = st.checkbox("1 x TP53 + del(17p)")
    with ctp3:
        tp53_loh = st.checkbox("1 x TP53 + LOH")

    st.markdown("#### MDS-related Mutation")
    sf3b1 = st.checkbox("SF3B1 mutation")

    st.markdown("#### MDS-related Cytogenetics")
    del_5q = st.checkbox("del(5q) / isolated 5q-")

    # Qualifiers
    st.markdown("#### Qualifiers")
    ql1, ql2 = st.columns(2)
    with ql1:
        prev_cytotx = st.checkbox("Previous cytotoxic therapy?")
    with ql2:
        germ_variant = st.text_input("Predisposing germline variant", value="None")

    return {
        "blasts_percentage": blasts,
        "fibrotic": fibrotic,
        "hypoplasia": hypoplasia,
        "number_of_dysplastic_lineages": int(dys_lineages),
        "Biallelic_TP53_mutation": {
            "2_x_TP53_mutations": tp53_2,
            "1_x_TP53_mutation_del_17p": tp53_17p,
            "1_x_TP53_mutation_LOH": tp53_loh
        },
        "MDS_related_mutation": {
            "SF3B1": sf3b1
        },
        "MDS_related_cytogenetics": {
            "del_5q": del_5q
        },
        "qualifiers": {
            "previous_cytotoxic_therapy": prev_cytotx,
            "predisposing_germline_variant": germ_variant.strip() if germ_variant.strip() else "None"
        }
    }


##############################
# HELPER: Build Manual AML RESPONSE DATA
##############################
def build_manual_aml_response_data() -> dict:
    """
    Builds a dictionary with all fields needed for classify_AML_Response_ELN2022 in a compact form.
    """
    st.markdown("### Manual AML Response Assessment (ELN 2022)")

    col1, col2 = st.columns(2)
    with col1:
        adequate_sample = st.checkbox("Adequate sample available?")
        bone_marrow_blasts = st.number_input("Bone Marrow Blasts (%)", min_value=0.0, max_value=100.0, value=0.0)
        blood_counts_provided = st.checkbox("Are blood counts provided?")
    with col2:
        platelets = st.number_input("Platelet count (x10^9/L)", min_value=0.0, value=0.0)
        neutrophils = st.number_input("Neutrophil count (x10^9/L)", min_value=0.0, value=0.0)

    st.markdown("#### Additional Response-Related Fields")
    col3, col4 = st.columns(2)
    with col3:
        previously_cr = st.checkbox("Previously achieved CR/CRh/CRi?")
        blasts_decrease_50 = st.checkbox("Blasts decreased by >= 50%?")
    with col4:
        tnc_5_25 = st.checkbox("Total nucleated cells (TNC) 5-25 x10^9/L?")

    # Convert booleans to your dictionary structure
    manual_response_data = {
        "AdequateSample": adequate_sample,
        "BoneMarrowBlasts": bone_marrow_blasts,
        "BloodCountsProvided": blood_counts_provided,
        "Platelets": platelets,
        "Neutrophils": neutrophils,
        "PreviouslyAchievedCR_CRh_Cri": previously_cr,
        "BlastsDecreaseBy50Percent": blasts_decrease_50,
        "TNCBetween5And25": tnc_5_25
    }
    return manual_response_data


##############################
# AML SECTION
##############################
def app_aml_section():
    st.subheader("Acute Myeloid Leukemia (AML) Classification")

    # Radio to choose Manual or AI mode
    aml_mode = st.radio("Input Mode:", ["Manual", "AI"], horizontal=True)

    if aml_mode == "Manual":
        st.markdown("**Manual Mode**: Fill out the form below to classify AML without free-text parsing.")

        manual_data = build_manual_aml_data()

        if st.button("Classify AML (Manual)"):
            classification_who, who_derivation = classify_AML_WHO2022(manual_data)
            classification_icc, icc_derivation = classify_AML_ICC2022(manual_data)

            display_aml_classification_results(
                manual_data,
                classification_who,
                who_derivation,
                classification_icc,
                icc_derivation,
                mode="manual"
            )
    else:
        st.markdown("**AI Mode**: Paste your free-text AML reports below. The system will parse and classify automatically.")

        blasts_input = st.text_input("Blasts Percentage (Override)", placeholder="e.g. 25")
        genetics_report = st.text_area("Genetics Report (AML):", height=100)
        cytogenetics_report = st.text_area("Cytogenetics Report (AML):", height=100)

        if st.button("Parse & Classify AML from Free-Text"):
            combined_report = f"{genetics_report}\n\n{cytogenetics_report}"
            if combined_report.strip():
                with st.spinner("Extracting data for AML classification..."):
                    parsed_fields = parse_genetics_report_aml(combined_report)

                    if blasts_input.strip():
                        try:
                            blasts_value = float(blasts_input.strip())
                            parsed_fields["blasts_percentage"] = blasts_value
                            st.info(f"Overridden blasts_percentage = {blasts_value}")
                        except ValueError:
                            st.warning("Invalid blasts percentage. Using parsed value.")

                if not parsed_fields:
                    st.warning("No data extracted or error in parsing.")
                else:
                    classification_who, who_derivation = classify_AML_WHO2022(parsed_fields)
                    classification_icc, icc_derivation = classify_AML_ICC2022(parsed_fields)

                    display_aml_classification_results(
                        parsed_fields,
                        classification_who,
                        who_derivation,
                        classification_icc,
                        icc_derivation,
                        mode="ai"
                    )
            else:
                st.error("Please provide genetics and/or cytogenetics report for AML.")


def display_aml_classification_results(parsed_fields, classification_who, who_derivation,
                                       classification_icc, icc_derivation, mode="manual"):
    """
    Helper function to display AML classification results and optionally AI review.
    """
    # Show extracted data
    with st.expander("### **View Parsed AML Values**", expanded=False):
        st.json(parsed_fields)

    # Display Classifications
    st.markdown("""
    <div style='background-color: #d1e7dd; padding: 15px; border-radius: 10px; margin-bottom: 20px;'>
        <h3 style='color: #0f5132;'>Classification Results</h3>
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### **WHO 2022 Classification**")
        st.markdown(f"**Classification:** {classification_who}")

    with col2:
        st.markdown("### **ICC 2022 Classification**")
        st.markdown(f"**Classification:** {classification_icc}")

    # Show derivations side-by-side
    col_who, col_icc = st.columns(2)
    with col_who:
        with st.expander("🔍 WHO 2022 Derivation", expanded=False):
            who_derivation_markdown = "\n\n".join(
                [f"**Step {idx}:** {step}" for idx, step in enumerate(who_derivation, start=1)]
            )
            st.markdown(who_derivation_markdown)

    with col_icc:
        with st.expander("🔍 ICC 2022 Derivation", expanded=False):
            icc_derivation_markdown = "\n\n".join(
                [f"**Step {idx}:** {step}" for idx, step in enumerate(icc_derivation, start=1)]
            )
            st.markdown(icc_derivation_markdown)

    # AI Review (optional)
    if st.session_state.get('authenticated', False):
        with st.spinner("Generating AI review and clinical next steps..."):
            combined_classifications = {
                "WHO 2022": {"Classification": classification_who},
                "ICC 2022": {"Classification": classification_icc}
            }
            gpt4_review_result = get_gpt4_review_aml(
                classification=combined_classifications,
                user_inputs=parsed_fields
            )
        st.info(gpt4_review_result)
    else:
        st.info("🔒 **Log in** for an AI-generated review and clinical recommendations.")

    # Final Disclaimer
    st.markdown("""
    ---
    <div style="background-color: #f8f9fa; padding: 10px; border-radius: 5px;">
        <p><strong>Disclaimer:</strong> This app is a simplified demonstration and <strong>not</strong> a replacement 
        for professional pathology review or real-world WHO/ICC classification.</p>
    </div>
    """, unsafe_allow_html=True)


##############################
# MDS SECTION
##############################
def app_mds_section():
    st.subheader("Myelodysplastic Syndromes (MDS) Classification")

    mds_mode = st.radio("Input Mode:", ["Manual", "AI"], horizontal=True)

    if mds_mode == "Manual":
        st.markdown("**Manual Mode**: Fill out the form below to classify MDS without free-text parsing.")

        manual_data = build_manual_mds_data()

        if st.button("Classify MDS (Manual)"):
            classification_who, derivation_who = classify_MDS_WHO2022(manual_data)
            classification_icc, derivation_icc = classify_MDS_ICC2022(manual_data)

            display_mds_classification_results(
                manual_data,
                classification_who,
                derivation_who,
                classification_icc,
                derivation_icc,
                mode="manual"
            )
    else:
        st.markdown("**AI Mode**: Paste your free-text MDS reports below. The system will parse and classify automatically.")

        blasts_override = st.text_input("Blasts Percentage (Override)", placeholder="e.g. 8")
        genetics_report = st.text_area("Genetics / Mutation Findings (MDS):", height=100)
        cytogenetics_report = st.text_area("Cytogenetics / Karyotype (MDS):", height=100)

        if st.button("Parse & Classify MDS from Free-Text"):
            combined_mds_report = f"{genetics_report}\n\n{cytogenetics_report}"
            if combined_mds_report.strip():
                with st.spinner("Parsing MDS data..."):
                    parsed_mds_fields = parse_genetics_report_mds(combined_mds_report)

                    if blasts_override.strip():
                        try:
                            override_blasts = float(blasts_override.strip())
                            parsed_mds_fields["blasts_percentage"] = override_blasts
                            st.info(f"Overridden blasts_percentage = {override_blasts}")
                        except ValueError:
                            st.warning("Invalid blasts percentage. Using parsed value.")

                if not parsed_mds_fields:
                    st.warning("No data extracted or an error occurred during MDS parsing.")
                else:
                    classification_who, derivation_who = classify_MDS_WHO2022(parsed_mds_fields)
                    classification_icc, derivation_icc = classify_MDS_ICC2022(parsed_mds_fields)

                    display_mds_classification_results(
                        parsed_mds_fields,
                        classification_who,
                        derivation_who,
                        classification_icc,
                        derivation_icc,
                        mode="ai"
                    )
            else:
                st.error("Please provide MDS genetics and/or cytogenetics report.")


def display_mds_classification_results(parsed_fields, classification_who, derivation_who,
                                       classification_icc, derivation_icc, mode="manual"):
    """
    Helper function to display MDS classification results for both WHO and ICC.
    """
    # Show parsed data
    with st.expander("View Parsed MDS Values", expanded=False):
        st.json(parsed_fields)

    st.markdown("""
    <div style='background-color: #d1e7dd; padding: 15px; border-radius: 10px; margin-bottom: 20px;'>
        <h3 style='color: #0f5132;'>MDS Classification Results</h3>
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### **WHO 2022 Classification**")
        st.write(classification_who)

    with col2:
        st.markdown("### **ICC 2022 Classification**")
        st.write(classification_icc)

    # Derivations
    col_who, col_icc = st.columns(2)
    with col_who:
        with st.expander("🔍 WHO 2022 Derivation", expanded=False):
            derivation_text = "\n\n".join(
                [f"**Step {i}**: {step}" for i, step in enumerate(derivation_who, start=1)]
            )
            st.markdown(derivation_text)

    with col_icc:
        with st.expander("🔍 ICC 2022 Derivation", expanded=False):
            derivation_text = "\n\n".join(
                [f"**Step {i}**: {step}" for i, step in enumerate(derivation_icc, start=1)]
            )
            st.markdown(derivation_text)

    # Optional AI review
    if st.session_state.get("authenticated", False):
        with st.spinner("Generating AI review and next steps..."):
            combined_mds_classifications = {
                "WHO 2022": {"Classification": classification_who},
                "ICC 2022": {"Classification": classification_icc}
            }
            review_result = get_gpt4_review_mds(
                classification=combined_mds_classifications,
                user_inputs=parsed_fields
            )
        st.info(review_result)
    else:
        st.info("🔒 **Log in** for an AI-generated review and recommendations.")

    # Disclaimer
    st.markdown("""
    ---
    <div style="background-color: #f8f9fa; padding: 10px; border-radius: 5px;">
        <p><strong>Disclaimer:</strong> This app is a simplified demonstration and <strong>not</strong> a replacement 
        for professional pathology review or real-world WHO/ICC classification.</p>
    </div>
    """, unsafe_allow_html=True)


##############################
# AML RESPONSE SECTION
##############################
def app_aml_response_assessment():
    st.subheader("AML Response Assessment (ELN 2022)")

    response_mode = st.radio("Input Mode:", ["Manual", "AI"], horizontal=True)

    if response_mode == "Manual":
        st.markdown("**Manual Mode**: Fill out the form below to assess AML response without free-text parsing.")
        manual_data = build_manual_aml_response_data()
        if st.button("Assess AML Response (Manual)"):
            response, derivation = classify_AML_Response_ELN2022(manual_data)
            display_aml_response_results(manual_data, response, derivation, "manual")
    else:
        st.markdown("**AI Mode**: Paste your free-text AML response findings below.")
        response_report = st.text_area("AML Response Report (Free-text):", height=120)
        if st.button("Assess AML Response (AI)"):
            if response_report.strip():
                with st.spinner("Extracting AML response data..."):
                    parsed_data = parse_aml_response_report(response_report)

                if not parsed_data:
                    st.warning("No data extracted or error in parsing.")
                else:
                    response, derivation = classify_AML_Response_ELN2022(parsed_data)
                    display_aml_response_results(parsed_data, response, derivation, "ai")
            else:
                st.error("Please provide a free-text AML response report.")


def display_aml_response_results(parsed_data, response, derivation, mode="manual"):
    """
    Displays the AML response assessment results (ELN 2022).
    """
    # Show the parsed/manual data
    with st.expander("### **View Parsed AML Response Values**", expanded=False):
        st.json(parsed_data)

    # Show classification
    st.markdown("""
    <div style='background-color: #d1e7dd; padding: 15px; border-radius: 10px; margin-bottom: 20px;'>
        <h3 style='color: #0f5132;'>AML Response Assessment Result</h3>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(f"### **{response}**")

    # Show derivation steps
    with st.expander("🔍 Derivation Steps", expanded=False):
        derivation_text = "\n\n".join([f"**Step {i}**: {step}" for i, step in enumerate(derivation, start=1)])
        st.markdown(derivation_text)

    # (Optional) AI Review if desired—similar to your other classifiers
    # If you want an AI review: 
    # - You'd define get_gpt4_review_aml_response(...) 
    # - Then call it below if st.session_state.get('authenticated', False)

    # Disclaimer
    st.markdown("""
    ---
    <div style="background-color: #f8f9fa; padding: 10px; border-radius: 5px;">
        <p><strong>Disclaimer:</strong> This AML response assessment is a simplified demonstration 
        and <strong>not</strong> a replacement for professional hematological review or real-world ELN criteria.</p>
    </div>
    """, unsafe_allow_html=True)



def app_main():
    st.title("Haematologic Classification & Response Assessment Tool")

    if st.session_state.get("authenticated", False):
        classification_choice = st.radio(
            "Select classification or assessment type:", 
            ("AML", "MDS", "AML Response Assessment (ELN 2022)")
        )

        if classification_choice == "AML":
            app_aml_section()
        elif classification_choice == "MDS":
            app_mds_section()
        else:
            app_aml_response_assessment()
    else:
        st.info("🔒 **Log in** to use the classification and response assessment features.")

    st.markdown("---")

def main():
    app_main()

if __name__ == "__main__":
    main()
