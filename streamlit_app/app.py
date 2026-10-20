"""Public presentation entry point; analysis runs separately before deployment.

No API keys, raw-data collection, filesystem mutation or model fitting occurs
when a visitor opens this app. All displayed results come from assets/.
"""
from pathlib import Path
import csv
import json
import streamlit as st

ROOT=Path(__file__).resolve().parent
ASSETS=ROOT/'assets'
st.set_page_config(page_title='Co-op merger competition explorer',page_icon='🗺️',layout='wide')


@st.cache_data
def cached_text(relative_path, modified_time):
    """Include file modification time so a new step-13 export invalidates cache."""
    return (ROOT/relative_path).read_text(encoding='utf-8')


def read_text(relative_path):
    return cached_text(relative_path,(ROOT/relative_path).stat().st_mtime_ns)


st.title('Co-op merger competition explorer')
st.caption('Independent portfolio project · published CMA convenience-screen rules applied to a separate dataset')
summary=json.loads(read_text('assets/analysis_summary.json'))
st.write(f"The current model flags **{summary['flagged_stores_core']} stores**, including **{summary['cma_locations_flagged_core']}** of the CMA’s **19** published concern locations.")
map_tab,method_tab,results_tab,report_tab=st.tabs(['Interactive map','Methodology','Results and downloads','Economics report'])

with map_tab:
    # An isolated iframe keeps Leaflet's globals and full-page CSS out of the
    # Streamlit document. Only the project's own generated HTML is supplied.
    explorer=st.components.v2.component('competition_explorer',js='''
export default function(component) {
    const frame=document.createElement('iframe');
    frame.title='Local competition map and rival evidence';
    frame.setAttribute('sandbox','allow-scripts allow-downloads');
    frame.style.cssText='width:100%;height:860px;border:0;display:block';
    frame.srcdoc=component.data.html;
    component.parentElement.appendChild(frame);
    return () => frame.remove();
}
''')
    explorer(data={'html':read_text('assets/competition_map.html')},key='competition_map')
with method_tab:
    st.markdown(read_text('docs/methodology.md'))
    with st.expander('Data sources and preparation boundary'):
        st.markdown(read_text('docs/data_sources.md'))
with results_tab:
    st.subheader('Published CMA concerns compared with our model')
    records=list(csv.DictReader(read_text('assets/benchmark_comparison.csv').splitlines()))
    st.dataframe(records,width='stretch',hide_index=True)
    for filename,label in [('benchmark_comparison.csv','CMA comparison'),('store_results.csv','All assessed stores'),
                           ('catchment_results.csv','Catchment scores'),('rival_contributions.csv','Rival contribution audit')]:
        st.download_button(label,read_text('assets/'+filename),file_name=filename,mime='text/csv')
    st.caption('Contribution rows describe observations. Group weights must be counted once per fascia and catchment.')
with report_tab:
    pdf=ROOT/'report/economics_report.pdf'
    markdown=ROOT/'report/economics_report.md'
    if markdown.exists():
        st.markdown(markdown.read_text(encoding='utf-8'))
    if pdf.exists():
        st.download_button('Download economics report',pdf.read_bytes(),file_name=pdf.name,mime='application/pdf')
    if not pdf.exists() and not markdown.exists():
        st.info('The author’s economics report will be added here. The map, methodology and model results are available now.')
st.caption('GEOLYTIX-primary records supplemented with OpenStreetMap · Esri/CARTO basemaps · this is not a CMA finding.')
