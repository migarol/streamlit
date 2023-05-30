import os
import pandas as pd
import sqlite3
import streamlit as st
from io import BytesIO
from langchain.chat_models import ChatOpenAI
from langchain import SQLDatabase, SQLDatabaseChain
from langchain.prompts.prompt import PromptTemplate
import re
import sys
from matplotlib import pyplot as plt
from io import StringIO

class FinanceAgent:
    def __init__(self, model_name="gpt-4", db_path="finance.db"):
        self.llm = ChatOpenAI(model_name=model_name)
        self.db = self.load_database(db_path)
        self.prompt = self.setup_prompt()
        self.thoughts = ""

    def load_database(self, db_path):
        dburi = f"sqlite:///{db_path}"
        custom_table_info = {
            'finance': """CREATE TABLE finance (
                "nombre_de_transaccion" NVARCHAR(200),
                "descripcion" NVARCHAR(200),
                "nickname" NVARCHAR(200),
                "fecha" DATE,
                "cantidad" FLOAT,
                "Tipo_de_transaccion" NVARCHAR(200),
                "categoria" NVARCHAR(200),
                "sub_categoria" NVARCHAR(200),
                "asset" NVARCHAR(200),
                "person" NVARCHAR(200),
                "person_type" NVARCHAR(200)
            )
            /*
            3 rows from finance table:
            nombre_de_transaccion	descripcion	nickname	fecha	cantidad	Tipo_de_transaccion	categoria	sub_categoria	asset	person	person_type
            1	AMERICAN EXPRESS    01429/ AEC810901 298   376701358071008	American express	American Express	4/28/2023	9000	GASTO	Not computable	Credit card payment		Yo	Yo
            9	RETIRO SIN TARJETA       / ******1458	Retiro sin tarjeta	Retiro Sin Tarjeta	4/28/2023	1500	GASTO	Gifts and help	Support for family and friends		Mama	Mama
            55	HM MX0011 PLAYACARMEN H SOLIDARIDAD	hm mx0011 playacarmen h solidaridad	hm	4/8/2023	778	GASTO	Gifts and help	Gifts		Amigas	friends
            */"""
        }
        db = SQLDatabase.from_uri(
            dburi,
            include_tables=['finance'],
            custom_table_info=custom_table_info
        )
        return db



    def setup_prompt(self):
        _DEFAULT_TEMPLATE = """
        Eres Klopp, un Coach de Finanzas Personales. Tu trabajo es asistir a los usuarios respondiendo preguntas sobre sus finanzas personales. Para hacer esto, necesitarás generar y ejecutar consultas SQL {dialect} en la base de datos 'finance.db', y luego o examinar los resultados de la consulta y responder con gran detalle e intentar brindar consejos para llevar una mejor vida financiera a nuestros usuarios.

        La base de datos 'finance.db' contiene una tabla llamada 'finance' con las siguientes columnas:

        - 'nombre_de_transaccion': El nombre de la transacción como viene del estadod e cuenta
        - 'descripcion': Una descripción de la transacción.
        - 'nickname': Un apodo para la transacción.
        - 'fecha': La fecha de la transacción.
        - 'cantidad': La cantidad de la transacción.
        - 'Tipo_de_transaccion': El tipo de transacción (por ejemplo, 'GASTO/INGRESO').
        - 'categoria': La categoría de la transacción.
        - 'sub_categoria': La subcategoría de la transacción.
        - 'asset': El activo involucrado en la transacción. (puede ser una casa, un coche, un negocio)
        - 'person': La persona involucrada en la transacción.(el nombre de la persona)
        - 'person_type': El tipo de persona involucrada en la transacción.(el parentesco, que puede ser, hijo, mama, friends, primo, etc.. )

    Aquí hay algunos ejemplos de los datos en la tabla 'finance':

        nombre_de_transaccion	descripcion	nickname	fecha	cantidad	Tipo_de_transaccion	categoria	sub_categoria	asset	person	person_type
        0	AMAZON MX*AMAZON RETAIL MEXICO CITY	amazon mx	Amazon Mx	4/11/2023	1070.75	GASTO	Not computable	Other not computable	depa Polanco	Arturo	Hijo
        12	IZI*CORPORACION BYA PAR PARACAS	Izi corporacion bya par paracas		5/14/2023	377.71	GASTO	Travels	Food on trips		Yo	Yo
        57	SPEI ENVIADO SCOTIABANK  / 0062340919  044 0205230Bby shower taboolars	Transferencia interbancaria (4; bby shower taboolars)	Transferencia Interbancaria	5/2/2023	6000	GASTO	Not computable	Other not computable		Georgina	Primo
    
    Aquí algunos ejemplos como referencia:
        Si un usuario pregunta '¿Cuánto gasté en regalos y ayuda en abril de 2023?', podrías generar la consulta SQL 'SELECT SUM(cantidad) FROM finance WHERE fecha LIKE '4/%/2023' AND categoria = 'Gifts and help'', ejecutar esta consulta en la base de datos y luego examinar los resultados de la consulta y responder con gran detalle e intentar brindar consejos para llevar una mejor vida financiera a nuestros usuarios.
        Si un usuario pregunta '¿Cuánto gasté en cada categoría en 2023?', podrías generar la consulta SQL 'SELECT categoria, SUM(cantidad) FROM finance WHERE fecha LIKE '%/2023' AND Tipo_de_transaccion = 'GASTO' GROUP BY categoria'', y luego proporcionar un desglose de los gastos del usuario por categoría.
        Si un usuario pregunta '¿Cuánto gasté en regalos y ayuda para mi mamá en 2023?', podrías generar la consulta SQL 'SELECT SUM(cantidad) FROM finance WHERE fecha LIKE '%/2023' AND categoria = 'Gifts and help' AND person = 'Mama'', y luego proporcionar un resumen de los gastos del usuario en regalos y ayuda para su mamá en ese año.
        Si un usuario pregunta '¿Cuánto gasté en mi familia en 2021?', podrías generar la consulta SQL 'SELECT SUM(cantidad) FROM finance WHERE fecha LIKE '%/2023' AND Tipo_de_transaccion = 'GASTO' AND person_type = 'Family Group'', y luego proporcionar un resumen de los gastos del usuario en su familia en ese año.
        Si un usuario pregunta '¿Cuánto gasté en cada miembro de mi familia ?', podrías generar la consulta SQL 'SELECT person, SUM(cantidad) FROM finance WHERE Tipo_de_transaccion = 'GASTO' AND person_type = 'Family Group' GROUP BY person'', y luego proporcionar un desglose de los gastos del usuario por cada miembro de la familia.
        Question: {input}
        """

        PROMPT = PromptTemplate(
            input_variables=["input", "dialect"], template=_DEFAULT_TEMPLATE
        )
        return PROMPT
    
    def chat_with_chatbot(self, query):
        db_chain = SQLDatabaseChain.from_llm(
            self.llm, self.db, verbose=True, prompt=self.prompt, use_query_checker=True
        )
        old_stdout = sys.stdout
        sys.stdout = captured_output = StringIO()
        try:
            result = db_chain.run(query)
        except Exception as e:
            print(f"Error executing query: {e}")
            result = db_chain.run(f"Correct the query: {query}")
        sys.stdout = old_stdout
        self.thoughts = self.process_agent_thoughts(captured_output)
        return result

    def process_agent_thoughts(self, captured_output):
        thoughts = captured_output.getvalue()
        cleaned_thoughts = re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', thoughts)
        cleaned_thoughts = re.sub(r'\[1m>', '', cleaned_thoughts)
        return cleaned_thoughts

    def display_agent_thoughts(self, cleaned_thoughts):
        with st.expander("Display the agent's thoughts"):
            st.write(cleaned_thoughts)

    def update_chat_history(self, query, result):
        st.session_state.chat_history.append(("user", query))
        st.session_state.chat_history.append(("agent", result))

    def display_chat_history(self):
        for i, (sender, message_text) in enumerate(st.session_state.chat_history):
            if sender == "user":
                st.write(f"User: {message_text}")
            else:
                st.write(f"Klopp: {message_text}")

st.set_page_config(layout="wide", page_icon="💬", page_title="Klopp | Assistant 🤖")

user_api_key = st.text_input("Enter your OpenAI API Key", value="", type="password")

if user_api_key:
    os.environ["OPENAI_API_KEY"] = user_api_key
    st.session_state.setdefault("reset_chat", False)

    uploaded_file = st.file_uploader("Upload a CSV or Excel file", type=["csv", "xlsx"])

    if uploaded_file:
        uploaded_file_content = BytesIO(uploaded_file.getvalue())
        if uploaded_file.type == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" or uploaded_file.type == "application/vnd.ms-excel":
            df = pd.read_excel(uploaded_file_content)
        else:
            df = pd.read_csv(uploaded_file_content)

        # Save the DataFrame to a SQLite database
        sqlite_file_path = './finance.db'
        conn = sqlite3.connect(sqlite_file_path)
        df.to_sql('finance', conn, if_exists="replace", index=False)
        conn.close()

        if "chat_history" not in st.session_state:
            st.session_state["chat_history"] = []
        finance_agent = FinanceAgent()

        with st.form(key="query"):
            query = st.text_input("Ask Klopp", value="", type="default", 
                placeholder="e-g : How many rows ? "
                )
            submitted_query = st.form_submit_button("Submit")
            reset_chat_button = st.form_submit_button("Reset Chat")
            if reset_chat_button:
                st.session_state["chat_history"] = []
        if submitted_query:
            result = finance_agent.chat_with_chatbot(query)
            finance_agent.display_agent_thoughts(finance_agent.thoughts)
            finance_agent.update_chat_history(query, result)
            finance_agent.display_chat_history()

        if df is not None:
            st.subheader("Current dataframe:")
            st.write(df)
        for i, (sender, message_text) in enumerate(st.session_state.chat_history):
            if sender == "user":
                st.write(f"User: {message_text}")
            else:
                st.write(f"Klopp: {message_text}")


