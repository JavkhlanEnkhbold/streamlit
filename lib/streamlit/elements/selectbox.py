# Copyright 2018-2021 Streamlit Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from typing import cast

import streamlit
from streamlit.errors import StreamlitAPIException
from streamlit.proto.Selectbox_pb2 import Selectbox as SelectboxProto
from streamlit.state.widgets import register_widget, NoValue
from streamlit.type_util import ensure_iterable
from streamlit.util import index_
from .form import current_form_id
from .utils import check_callback_rules, check_session_state_rules


class SelectboxMixin:
    def selectbox(
        self,
        label,
        options,
        index=0,
        format_func=str,
        key=None,
        help=None,
        on_change=None,
        args=None,
        kwargs=None,
    ):
        """Display a select widget.

        Parameters
        ----------
        label : str
            A short label explaining to the user what this select widget is for.
        options : list, tuple, numpy.ndarray, pandas.Series, or pandas.DataFrame
            Labels for the select options. This will be cast to str internally
            by default. For pandas.DataFrame, the first column is selected.
        index : int
            The index of the preselected option on first render.
        format_func : function
            Function to modify the display of the labels. It receives the option
            as an argument and its output will be cast to str.
        key : str
            An optional string to use as the unique key for the widget.
            If this is omitted, a key will be generated for the widget
            based on its content. Multiple widgets of the same type may
            not share the same key.
        help : str
            An optional tooltip that gets displayed next to the selectbox.
        on_change : callable
            An optional callback invoked when this selectbox's value changes.
        args : tuple
            An optional tuple of args to pass to the callback.
        kwargs : dict
            An optional dict of kwargs to pass to the callback.

        Returns
        -------
        any
            The selected option

        Example
        -------
        >>> option = st.selectbox(
        ...     'How would you like to be contacted?',
        ...     ('Email', 'Home phone', 'Mobile phone'))
        >>>
        >>> st.write('You selected:', option)

        """
        check_callback_rules(self.dg, on_change)
        check_session_state_rules(default_value=None if index == 0 else index, key=key)

        options = ensure_iterable(options)

        if not isinstance(index, int):
            raise StreamlitAPIException(
                "Selectbox Value has invalid type: %s" % type(index).__name__
            )

        if len(options) > 0 and not 0 <= index < len(options):
            raise StreamlitAPIException(
                "Selectbox index must be between 0 and length of options"
            )

        selectbox_proto = SelectboxProto()
        selectbox_proto.label = label
        selectbox_proto.default = index
        selectbox_proto.options[:] = [str(format_func(option)) for option in options]
        selectbox_proto.form_id = current_form_id(self.dg)
        if help is not None:
            selectbox_proto.help = help

        def deserialize_select_box(ui_value):
            idx = ui_value if ui_value is not None else index

            return (
                options[idx] if len(options) > 0 and options[idx] is not None else None
            )

        def serialize_select_box(v):
            return index_(options, v)

        current_value, set_frontend_value = register_widget(
            "selectbox",
            selectbox_proto,
            user_key=key,
            on_change_handler=on_change,
            args=args,
            kwargs=kwargs,
            deserializer=deserialize_select_box,
            serializer=serialize_select_box,
        )

        if set_frontend_value:
            selectbox_proto.value = serialize_select_box(current_value)
            selectbox_proto.set_value = True

        self.dg._enqueue("selectbox", selectbox_proto)
        return current_value

    @property
    def dg(self) -> "streamlit.delta_generator.DeltaGenerator":
        """Get our DeltaGenerator."""
        return cast("streamlit.delta_generator.DeltaGenerator", self)
