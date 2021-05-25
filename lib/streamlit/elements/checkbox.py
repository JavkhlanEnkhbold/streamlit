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

from typing import cast, Optional

import streamlit
from streamlit.proto.Checkbox_pb2 import Checkbox as CheckboxProto
from streamlit.state.widgets import (
    register_widget,
    WidgetArgs,
    WidgetCallback,
    WidgetDeserializer,
    WidgetKwargs,
)
from .form import current_form_id


class CheckboxMixin:
    def checkbox(
        self,
        label: str,
        value: Optional[bool] = False,
        key: Optional[str] = None,
        help: Optional[str] = None,
        on_change: Optional[WidgetCallback] = None,
        args: Optional[WidgetArgs] = None,
        kwargs: Optional[WidgetKwargs] = None,
    ) -> bool:
        """Display a checkbox widget.

        Parameters
        ----------
        label : str
            A short label explaining to the user what this checkbox is for.
        value : Optional[bool]
            Preselect the checkbox when it first renders. This will be
            cast to bool internally.
        key : Optional[str]
            An optional string to use as the unique key for the widget.
            If this is omitted, a key will be generated for the widget
            based on its content. Multiple widgets of the same type may
            not share the same key.
        help : Optional[str]
            A tooltip that gets displayed next to the checkbox.
        on_change : Optional[Callable]
            An optional callback invoked when the checkbox is toggled.
        args : Optional[Tuple]
            An optional tuple of args to pass to the callback.
        kwargs : Optional[Dict]
            An optional dict of kwargs to pass to the callback.

        Returns
        -------
        bool
            Whether or not the checkbox is checked.

        Example
        -------
        >>> agree = st.checkbox('I agree')
        >>>
        >>> if agree:
        ...     st.write('Great!')

        """
        checkbox_proto = CheckboxProto()
        checkbox_proto.label = label
        checkbox_proto.default = bool(value)
        checkbox_proto.form_id = current_form_id(self.dg)
        if help is not None:
            checkbox_proto.help = help

        deserialize_checkbox: WidgetDeserializer = lambda ui_value: bool(
            ui_value if ui_value is not None else value
        )
        current_value, set_frontend_value = register_widget(
            "checkbox",
            checkbox_proto,
            user_key=key,
            on_change_handler=on_change,
            args=args,
            kwargs=kwargs,
            deserializer=deserialize_checkbox,
        )

        if set_frontend_value:
            checkbox_proto.value = current_value
            checkbox_proto.set_value = True

        self.dg._enqueue("checkbox", checkbox_proto)
        return current_value

    @property
    def dg(self) -> "streamlit.delta_generator.DeltaGenerator":
        """Get our DeltaGenerator."""
        return cast("streamlit.delta_generator.DeltaGenerator", self)
