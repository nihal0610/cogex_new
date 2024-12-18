import streamlit as st
import openai
import pandas as pd
import pyodbc
import json

def generate_sql_query(user_prompt, table_name, column_names):
    try:
        columns_description = ", ".join(column_names)
        schema_info = f"The table '{table_name}' has the following columns: {columns_description}."

        system_message = (
            "You are an expert query generator. "
            "Create SQL queries based on the given description. "
            "The table always uses the name '{table_name}'. "
            "Only use the column names provided in the schema. "
            "Do not insert the query as commented code. "
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
        return f"Error generating SQL query: {str(e)}"

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

        # Azure SQL Database connection
        server = 'your_server.database.windows.net'
        database = 'your_database'
        username = 'your_username'
        password = 'your_password'
        driver = '{ODBC Driver 17 for SQL Server}'
        connection_string = f'DRIVER={driver};SERVER={server};PORT=1433;DATABASE={database};UID={username};PWD={password}'
        conn = pyodbc.connect(connection_string)
        cursor = conn.cursor()

        # Drop table if it exists
        table_name = 'utilisation'
        cursor.execute(f"IF OBJECT_ID('{table_name}', 'U') IS NOT NULL DROP TABLE {table_name}")

        # Create table based on the DataFrame
        create_table_query = f"CREATE TABLE {table_name} ({', '.join([f'{col} NVARCHAR(MAX)' for col in df.columns])})"
        cursor.execute(create_table_query)
        conn.commit()

        # Insert data into Azure SQL Database
        insert_query = f"INSERT INTO {table_name} ({', '.join(df.columns)}) VALUES ({', '.join(['?' for _ in df.columns])})"
        for _, row in df.iterrows():
            cursor.execute(insert_query, tuple(row))
        conn.commit()

        column_names = df.columns.tolist()
        query = generate_sql_query(user_prompt, table_name, column_names)

        # Execute query and fetch results
        cursor.execute(query)
        columns = [column[0] for column in cursor.description]
        result_df = pd.DataFrame(cursor.fetchall(), columns=columns)

        conn.close()

        if not result_df.empty:
            return query, result_df
        else:
            return query, "No results found."
    except Exception as e:
        return f"Error: {e}", None

def main():
    st.title("Azure SQL Database Query Generator")
    st.write("Provide your OpenAI API key, upload an Excel file, and enter a description to generate a SQL query using GPT-3.5 Turbo.")

    api_key = st.text_input("OpenAI API Key", type="password")
    uploaded_file = st.file_uploader("Upload your Excel file")
    user_prompt = st.text_input("Describe the SQL query you need")

    if api_key and uploaded_file and user_prompt:
        query, result = process_file(api_key, uploaded_file, user_prompt)

        st.write("### Generated SQL Query")
        st.code(query)

        if isinstance(result, pd.DataFrame):
            st.write("### Query Results")
            st.dataframe(result)
        else:
            st.write("### Query Results")
            st.write(result)

if __name__ == "__main__":
    main()
