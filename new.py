import streamlit as st
import openai
import pandas as pd
from pymongo import MongoClient

def generate_sql_query(user_prompt, column_names):
    try:
        columns_description = ", ".join(column_names)
        schema_info = f"The table 'utilisation' has the following columns: {columns_description}."

        system_message = (
            "You are an expert SQL generator. "
            "You should only generate code that is supported in MongoDB. "
            "Create only MongoDB queries based on the given description. "
            "The table always uses the name 'utilisation'. "
            "Only use the column names provided in the schema. "
            "Do not insert the MongoDB query as commented code. "
        )
        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": f"{schema_info}\n\n{user_prompt}"}
        ]

        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=messages,
            temperature=0,
            max_tokens=200
        )

        query = response.choices[0].message.content.strip()
        return query
    except Exception as e:
        return f"Error generating MongoDB query: {str(e)}"

def process_file(api_key, uploaded_file, user_prompt):
    try:
        openai.api_key = api_key
        df = pd.read_excel(uploaded_file)
        date_cols = ['ProjectEnddate', 'ProjectStartdate', 'AllocationStartDate', 'AllocationEndDate']
        for date_column in date_cols:
            if date_column in df.columns:
                df[date_column] = pd.to_datetime(df[date_column], errors='coerce')

        df.columns = [col.strip().replace("  ", "").replace(" / ", "").replace("-", "").replace(" ", "") for col in df.columns]
        df = df.fillna("NULL")

        # MongoDB connection
        uri = "mongodb+srv://nihalk0610:chotu0610@cluster0.ldao3.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
        client = MongoClient(uri)
        db = client['your_database_name']
        collection = db['utilisation']

        # Drop collection if it exists
        collection.drop()

        # Insert data into MongoDB
        data = df.to_dict(orient='records')
        collection.insert_many(data)

        column_names = df.columns.tolist()
        query = generate_sql_query(user_prompt, column_names)

        # Execute query and fetch results
        result = collection.find(query)
        result_df = pd.DataFrame(list(result))

        client.close()

        if not result_df.empty:
            return query, result_df
        else:
            return query, "No results found."
    except Exception as e:
        return f"Error: {e}", None

def main():
    st.title("MongoDB Query Generator")
    st.write("Provide your OpenAI API key, upload an Excel file, and enter a description to generate a MongoDB query using GPT-3.5 Turbo.")

    api_key = st.text_input("OpenAI API Key", type="password")
    uploaded_file = st.file_uploader("Upload your Excel file")
    user_prompt = st.text_input("Describe the MongoDB query you need")

    if api_key and uploaded_file and user_prompt:
        query, result = process_file(api_key, uploaded_file, user_prompt)

        st.write("### Generated MongoDB Query")
        st.code(query)

        if isinstance(result, pd.DataFrame):
            st.write("### Query Results")
            st.dataframe(result)
        else:
            st.write("### Query Results")
            st.write(result)

if __name__ == "__main__":
    main()
