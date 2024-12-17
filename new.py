import streamlit as st
import openai
import pandas as pd
import pymysql
from mysql.connector import Error

def fetch_table_schema(cursor, table_name):
    cursor.execute(f"DESCRIBE {table_name}")
    schema = cursor.fetchall()
    column_names = [col[0] for col in schema]
    return column_names

def generate_sql_query(user_prompt, column_names):
    try:
        columns_description = ", ".join(column_names)
        schema_info = f"The table 'utilisation' has the following columns: {columns_description}."

        system_message = (
            "You are an expert SQL generator. "
            "You should only generate code that is supported in MySQL. "
            "Create only SQL SELECT queries based on the given description. "
            "The table always uses the name 'utilisation'. "
            "Only use the column names provided in the schema. "
            "Do not insert the SQL query as commented code. "
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

        sql_query = response.choices[0].message.content.strip()
        return sql_query
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

        connection = pymysql.connect(
            host="localhost",
            user="root",
            password="chotu0610",
            database="genai"
        )
        cursor = connection.cursor()

        table_name = "utilisation"
        cursor.execute(f"DROP TABLE IF EXISTS {table_name};")

        create_table_query = f"""
        CREATE TABLE {table_name} (
            {', '.join([f'`{col}` TEXT' for col in df.columns])}
        );
        """
        cursor.execute(create_table_query)

        for _, row in df.iterrows():
            insert_query = f"INSERT INTO {table_name} VALUES ({', '.join(['%s'] * len(row))})"
            cursor.execute(insert_query, tuple(row))
        connection.commit()

        column_names = df.columns.tolist()
        sql_query = generate_sql_query(user_prompt, column_names)

        cursor.execute(sql_query)
        result = cursor.fetchall()

        cursor.close()
        connection.close()

        if result:
            result_df = pd.DataFrame(result, columns=[desc[0] for desc in cursor.description])
            return sql_query, result_df
        else:
            return sql_query, "No results found."
    except Error as e:
        return f"Error: {e}", None

def main():
    st.title("SQL Query Generator")
    st.write("Provide your OpenAI API key, upload an Excel file, and enter a description to generate an SQL SELECT query using GPT-3.5 Turbo.")

    api_key = st.text_input("OpenAI API Key", type="password")
    uploaded_file = st.file_uploader("Upload your Excel file")
    user_prompt = st.text_input("Describe the SQL query you need")

    if api_key and uploaded_file and user_prompt:
        sql_query, result = process_file(api_key, uploaded_file, user_prompt)

        st.write("### Generated SQL Query")
        st.code(sql_query)

        if isinstance(result, pd.DataFrame):
            st.write("### Query Results")
            st.dataframe(result)
        else:
            st.write("### Query Results")
            st.write(result)

if __name__ == "__main__":
    main()
