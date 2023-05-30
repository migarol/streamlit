import os
import sys
import re
from io import StringIO, BytesIO
import pandas as pd
import sqlite3
import streamlit as st

from langchain import SQLDatabase, SQLDatabaseChain
from langchain.chat_models import ChatOpenAI
from langchain.prompts.prompt import PromptTemplate


# Constantes
MODEL_NAME = "gpt-4"
DEFAULT_TEMPLATE = """
Eres Klopp, un Coach de Finanzas Personales, que ayudará al usuario a responder preguntas basadas en sus finanzas. Siempre debes responder con la consulta correcta unicamente con un SQL {dialect} para ejecutar, luego examinar los resultados de la consulta y responder con gran detalle e intentar brindar consejos para llevar una mejor vida financiera a nuestros usuarios.
Utiliza la tabla finance para las consultas.
acá un ejemplo de fianance
    nombre de transaccion    descripcion    nickname    fecha    cantidad    Tipo de transaccion    categoria    sub_categoria    asset    person    person_type
1    AMERICAN EXPRESS    01429/ AEC810901 298   376701358071008    American express    American Express    4/28/2023    9000    GASTO    Not computable    Credit card payment        Yo    Yo
9    RETIRO SIN TARJETA       / ******1458    Retiro sin tarjeta    Retiro Sin Tarjeta    4/28/2023    1500    GASTO    Gifts and help    Support for family and friends        Mama    Mama
55    HM MX0011 PLAYACARMEN H SOLIDARIDAD    hm mx0011 playacarmen h solidaridad    hm    4/8/2023    778    GASTO    Gifts and help    Gifts        Amigas    friends
28	OPENPAY*HELPHBOMAXCOM CUAUHTEMOC	hbo	Hbo	4/5/2023	89.5	GASTO	Utilities	Streaming services (Netflix, HBO, Disney Plus)	depa Polanco	Arturo	Hijo

Question: {input}
"""

class FinanceAgent:
    def __init__(self, model_name="gpt-4", db_path="finance.db"):
        self.llm = ChatOpenAI(model_name=model_name)
        self.db = self.load_database(db_path)
        self.prompt = self.setup_prompt()

    def load_database(self, db_path):
        dburi = f"sqlite:///{db_path}"
        db = SQLDatabase.from_uri(
            dburi,
            sample_rows_in_table_info=3,
            include_tables=['finance']
        )
        return db


    def setup_prompt(self):
        PROMPT = PromptTemplate(
            input_variables=["input", "dialect"], template=DEFAULT_TEMPLATE
        )
        return PROMPT

    def chat_with_chatbot(self, query):
        old_stdout = sys.stdout
        sys.stdout = captured_output = StringIO()
        self.db_chain = SQLDatabaseChain.from_llm(self.llm, self.db, verbose=True, prompt=self.prompt, use_query_checker=True)
        result = self.db_chain.run(query)
        sys.stdout = old_stdout
        self.captured_output = captured_output.getvalue()
        return result


    def process_agent_thoughts(self):
        cleaned_thoughts = re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', self.captured_output)
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

user_api_key = st.text_input("OpenAI Api Key", value="", type="password")

if user_api_key:
    os.environ["OPENAI_API_KEY"] = user_api_key
    st.session_state.setdefault("reset_chat", False)

    uploaded_file = st.file_uploader("Sube tu archivo de finanzas Klopp", type=["csv", "xlsx"])

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
            query = st.text_input("Preguntale a Klopp", value="", type="default", 
                placeholder="e-g : Cuanto he gastado en "
                )
            submitted_query = st.form_submit_button("Submit")
            reset_chat_button = st.form_submit_button("Reset Chat")
            if reset_chat_button:
                st.session_state["chat_history"] = []
        if submitted_query:
            result = finance_agent.chat_with_chatbot(query)
            cleaned_thoughts = finance_agent.process_agent_thoughts()
            finance_agent.display_agent_thoughts(cleaned_thoughts)
            finance_agent.update_chat_history(query, result)
            finance_agent.display_chat_history()

        if df is not None:
            st.subheader("Mis Transacciones:")
            st.write(df)
        for i, (sender, message_text) in enumerate(st.session_state.chat_history):
            if sender == "user":
                st.write(f"User: {message_text}")
            else:
                st.write(f"Klopp: {message_text}")
