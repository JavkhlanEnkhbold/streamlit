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

from typing import cast, List, Optional, Union

import streamlit
from streamlit import config
from streamlit.logger import get_logger
from streamlit.proto.FileUploader_pb2 import FileUploader as FileUploaderProto
from streamlit.report_thread import get_report_ctx
from streamlit.state.widgets import register_widget, NoValue
from .form import current_form_id
from ..proto.Common_pb2 import SInt64Array
from ..uploaded_file_manager import UploadedFile, UploadedFileRec
from .utils import check_callback_rules, check_session_state_rules

LOGGER = get_logger(__name__)


class FileUploaderMixin:
    def file_uploader(
        self,
        label,
        type=None,
        accept_multiple_files=False,
        key=None,
        help=None,
        on_change=None,
        args=None,
        kwargs=None,
    ):
        """Display a file uploader widget.
        By default, uploaded files are limited to 200MB. You can configure
        this using the `server.maxUploadSize` config option.

        Parameters
        ----------
        label : str
            A short label explaining to the user what this file uploader is for.

        type : str or list of str or None
            Array of allowed extensions. ['png', 'jpg']
            The default is None, which means all extensions are allowed.

        accept_multiple_files : bool
            If True, allows the user to upload multiple files at the same time,
            in which case the return value will be a list of files.
            Default: False

        key : str
            An optional string to use as the unique key for the widget.
            If this is omitted, a key will be generated for the widget
            based on its content. Multiple widgets of the same type may
            not share the same key.

        help : str
            A tooltip that gets displayed next to the file uploader.

        on_change : callable
            An optional callback invoked when this file_uploader's value
            changes.

        args : tuple
            An optional tuple of args to pass to the callback.

        kwargs : dict
            An optional dict of kwargs to pass to the callback.

        Returns
        -------
        None or UploadedFile or list of UploadedFile
            - If accept_multiple_files is False, returns either None or
              an UploadedFile object.
            - If accept_multiple_files is True, returns a list with the
              uploaded files as UploadedFile objects. If no files were
              uploaded, returns an empty list.

            The UploadedFile class is a subclass of BytesIO, and therefore
            it is "file-like". This means you can pass them anywhere where
            a file is expected.

        Examples
        --------
        Insert a file uploader that accepts a single file at a time:

        >>> uploaded_file = st.file_uploader("Choose a file")
        >>> if uploaded_file is not None:
        ...     # To read file as bytes:
        ...     bytes_data = uploaded_file.getvalue()
        ...     st.write(bytes_data)
        >>>
        ...     # To convert to a string based IO:
        ...     stringio = StringIO(uploaded_file.getvalue().decode("utf-8"))
        ...     st.write(stringio)
        >>>
        ...     # To read file as string:
        ...     string_data = stringio.read()
        ...     st.write(string_data)
        >>>
        ...     # Can be used wherever a "file-like" object is accepted:
        ...     dataframe = pd.read_csv(uploaded_file)
        ...     st.write(dataframe)

        Insert a file uploader that accepts multiple files at a time:

        >>> uploaded_files = st.file_uploader("Choose a CSV file", accept_multiple_files=True)
        >>> for uploaded_file in uploaded_files:
        ...     bytes_data = uploaded_file.read()
        ...     st.write("filename:", uploaded_file.name)
        ...     st.write(bytes_data)
        """
        check_callback_rules(self.dg, on_change)
        check_session_state_rules(default_value=None, key=key, writes_allowed=False)

        if type:
            if isinstance(type, str):
                type = [type]

            # May need a regex or a library to validate file types are valid
            # extensions.
            type = [
                file_type if file_type[0] == "." else f".{file_type}"
                for file_type in type
            ]

        file_uploader_proto = FileUploaderProto()
        file_uploader_proto.label = label
        file_uploader_proto.type[:] = type if type is not None else []
        file_uploader_proto.max_upload_size_mb = config.get_option(
            "server.maxUploadSize"
        )
        file_uploader_proto.multiple_files = accept_multiple_files
        file_uploader_proto.form_id = current_form_id(self.dg)
        if help is not None:
            file_uploader_proto.help = help

        # TODO: Fix this (de)serializer so that st.session_state[key] can be
        #       used to access an uploaded file.
        def deserialize_file_uploader(ui_value):
            return ui_value

        def serialize_file_uploader(v):
            return v

        # FileUploader's widget value is a list of file IDs
        # representing the current set of files that this uploader should
        # know about.
        widget_value, _ = register_widget(
            "file_uploader",
            file_uploader_proto,
            user_key=key,
            on_change_handler=on_change,
            args=args,
            kwargs=kwargs,
            deserializer=deserialize_file_uploader,
            serializer=serialize_file_uploader,
        )

        file_recs = self._get_file_recs(file_uploader_proto.id, widget_value)
        return_value: Optional[Union[List[UploadedFile], UploadedFile]] = None
        if len(file_recs) == 0:
            return_value = [] if accept_multiple_files else None
        else:
            files = [UploadedFile(rec) for rec in file_recs]
            return_value = files if accept_multiple_files else files[0]

        self.dg._enqueue("file_uploader", file_uploader_proto)
        return return_value

    @staticmethod
    def _get_file_recs(
        widget_id: str, widget_value: Optional[List[int]]
    ) -> List[UploadedFileRec]:
        if widget_value is None:
            return []

        ctx = get_report_ctx()
        if ctx is None:
            return []

        if len(widget_value) == 0:
            # Sanity check
            LOGGER.warning(
                "Got an empty FileUploader widget_value. (We expect a list with at least one value in it.)"
            )
            return []

        # The first number in the widget_value list is 'newestServerFileId'
        newest_file_id = widget_value[0]
        active_file_ids = list(widget_value[1:])

        # Grab the files that correspond to our active file IDs.
        file_recs = ctx.uploaded_file_mgr.get_files(
            session_id=ctx.session_id,
            widget_id=widget_id,
            file_ids=active_file_ids,
        )

        # Garbage collect "orphaned" files.
        ctx.uploaded_file_mgr.remove_orphaned_files(
            session_id=ctx.session_id,
            widget_id=widget_id,
            newest_file_id=newest_file_id,
            active_file_ids=active_file_ids,
        )

        return file_recs

    @property
    def dg(self) -> "streamlit.delta_generator.DeltaGenerator":
        """Get our DeltaGenerator."""
        return cast("streamlit.delta_generator.DeltaGenerator", self)
