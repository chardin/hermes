# -*- coding: utf-8 -*-
"""forms - Form objects for the Hermes UI

This module supplies form objects to be used in building UIs.

Example:

.. code-block:: python3

    import forms
    form = LoginForm()
    if form.validate_on_submit():
        ...

"""

from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, \
    SelectField
from wtforms.validators import DataRequired


class LoginForm(FlaskForm):
    """A login form for the Hermes UI.

    This class supplies UI form fields to support a login page.
    """

    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')


class PickRoutineForm(FlaskForm):
    """A routine selection form for the Hermes UI.

    This class supplies UI form fields to support selecting
    a routine.
    """

    routine_choices = SelectField('Routine', choices=[], validate_choice=False)
    submit = SubmitField('Select Routine')


class RecordRoutineForm(FlaskForm):
    """A form to record the performance of a routine
    for the Hermes UI.

    This class supplies a UI form field to support recording
    the fact that the user performed the given routine.
    """

    submit = SubmitField('Record Progress')
