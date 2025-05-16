"""
Modern session state handler for Streamlit 1.x+

Usage
-----

>>> import SessionState
>>> session_state = SessionState.get(user_name='', favorite_color='black')
>>> session_state.user_name
''
>>> session_state.user_name = 'Mary'
>>> session_state.favorite_color
'black'

# On rerun:
>>> session_state = SessionState.get(user_name='', favorite_color='black')
>>> session_state.user_name
'Mary'
"""

import streamlit as st

class SessionState:
    def __init__(self, **kwargs):
        """Initialize session state with default values."""
        for key, value in kwargs.items():
            setattr(self, key, value)

def get(**kwargs):
    """
    Retrieve or create a SessionState object in Streamlit session.
    
    Parameters
    ----------
    **kwargs : key-value pairs
        Default values for the session state.

    Returns
    -------
    SessionState
        The session state object with saved attributes.
    """
    if 'session_state_instance' not in st.session_state:
        st.session_state['session_state_instance'] = SessionState(**kwargs)
    return st.session_state['session_state_instance']
