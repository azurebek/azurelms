from pydantic import BaseModel
from typing import Any

class BaseSmartForm(BaseModel):
    """
    Base class for all AI conversational forms.
    Inherits from Pydantic BaseModel for automatic field validation.
    """

    def submit(self, user) -> Any:
        """
        Handles saving the validated form data.
        Must be overridden by subclasses.
        Should return an event or payload indicating completion.
        """
        raise NotImplementedError("Subclasses must implement submit()")
