import pandas as pd
import gradio as gr
from openai import AzureOpenAI
from langchain_experimental.agents.agent_toolkits import create_pandas_dataframe_agent
from langchain.chat_models import ChatOpenAI
from datetime import datetime
 
def analyze_project(openai_api_key, uploaded_file, project_type, date_type, days, days_type, comparison):
    if not openai_api_key:
        return "Please enter your OpenAI API key.", None
 
    if uploaded_file is None:
        return "Please upload your Excel file.", None
 
    ddf = pd.read_excel(uploaded_file)
    llm = ChatOpenAI(
        openai_api_key=openai_api_key,
        temperature=0,
        max_tokens=4000,
        model_name="gpt-3.5-turbo-16k"
    )
 
    ddf['ProjectEnddate2'] = pd.to_datetime(ddf['ProjectEnddate'])
    ddf['Days_Remaining'] = (ddf['ProjectEnddate2'] - datetime.now()).dt.days
    ddf['ProjectStartdate1'] = pd.to_datetime(ddf['ProjectStartdate'])
    ddf['Days_passed'] = (datetime.now() - ddf['ProjectStartdate1']).dt.days
 
    input_query = f"Give me IDs of all managers in a list format, whose days_{days_type} from {date_type} is {comparison} {days} and project type is {project_type}"
    agent = create_pandas_dataframe_agent(llm, ddf, verbose=False, allow_dangerous_code=True, full_output=False, max_iterations=100)
    result1 = agent.invoke(input_query)
    value = result1['output']
 
    if isinstance(value, str):
        value = value.strip('[]').split(', ')
        value = [v.strip("'") for v in value]
        value = [int(v) for v in value]
 
    filtered_df = ddf[ddf["Manager ID"].isin(value)][["Manager ID", "Project Name", "Project Id"]]
    return "Result:", filtered_df
 
def main():
    with gr.Blocks() as demo:
        gr.Markdown("# Manager Project Analysis")
 
        openai_api_key = gr.Textbox(label="Enter your OpenAI API key", type="password")
        uploaded_file = gr.File(label="Upload your Excel file")
        project_type = gr.Dropdown(label="Please select one project type", choices=['MGMNT','EXTN','SALES','PDP','INFRA','TCE','CRPIT','DMGMT','INVMT','CORP','RCMNT','BENCH','EXANT','MKTAL','OPS','CAPEX','UAMCP','ELT','GGMS','PRDCG'])
        date_type = gr.Dropdown(label="Please select from which Project date you want to calculate days", choices=['Project start date','Project end date'])
        days = gr.Textbox(label="Please enter the days")
        days_type = gr.Dropdown(label="Please select the days passed from the date or remaining to the date", choices=['Passed','Remaining'])
        comparison = gr.Dropdown(label="Please select either you want the results to be equal, greater or less than the amount of days you specify", choices=['Equal to','Greater than','Less than'])
        submit_button = gr.Button("Submit")
 
        output_text = gr.Textbox(label="Result")
        output_df = gr.DataFrame(label="Filtered Data")
 
        submit_button.click(analyze_project, inputs=[openai_api_key, uploaded_file, project_type, date_type, days, days_type, comparison], outputs=[output_text, output_df])
 
    demo.launch()
 
if __name__ == "__main__":
    main()
