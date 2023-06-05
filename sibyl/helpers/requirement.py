from enum import Enum
import bs4


class RequirementType(Enum):
    SCRIPT = 1
    STYLE = 2


class Requirement:
    """A CSS or JS file that is required by a component."""

    name: str
    type: RequirementType
    path: str

    def __init__(self, name, type, path):
        """Create a new requirement."""
        self.name = name
        self.type = type
        self.path = path

    def to_dict(self):
        """Convert the requirement to a dictionary."""
        path = self.path
        # if the path isn't to an absolute URL, add a slash to the start
        if (
            not path.lower().startswith("http://")
            and not path.lower().startswith("https://")
            and not path.startswith("/")
        ):
            path = "/" + path
        return {"type": self.type.name, "path": path}

    def __hash__(self):
        return (self.name, self.type).__hash__()

    def __eq__(self, other):
        return self.name == other.name and self.type == other.type

    def to_tag(self) -> bs4.Tag:
        """Convert the requirement to a tag."""
        path = self.path
        # if the path isn't to an absolute URL, add a slash to the start
        if (
            not path.lower().startswith("http://")
            and not path.lower().startswith("https://")
            and not path.startswith("/")
        ):
            path = "/" + path
        if self.type == RequirementType.SCRIPT:
            return bs4.Tag(name="script", attrs={"defer": "", "src": path})
        elif self.type == RequirementType.STYLE:
            return bs4.Tag(
                name="link",
                attrs={"rel": "stylesheet", "href": path},
                can_be_empty_element=True,
            )
        else:
            raise ValueError("Unknown requirement type: " + self.type.name)
