import re
import datetime

from fw_client import FWClient
from fw_http_client.errors import NotFound

CONTAINER_ID_FORMAT = "^[0-9a-fA-F]{24}$"
SNAPSHOT_TIMESTAMP_FORMAT = "%Y-%m-%dT%H:%M:%S.%f%z"
RECORD_TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M"


class SnapshotState(str, Enum):
    """The snapshot state"""

    pending = "pending"
    in_progress = "in_progress"
    complete = "complete"
    failed = "failed"

    def is_final(self) -> bool:
        """Helper that indicates whether or not this is a terminal state"""
        return self in (SnapshotState.complete, SnapshotState.failed)


class SnapshotParents(BaseModel):
    """Parent references for snapshots"""
    project: str


class SnapshotRecord(BaseModel):
    id: str = Field(alias="_id")
    created: datetime = Field(default_factory=datetime.now(timezone.utc))
    status: SnapshotState
    parents: SnapshotParents
    group_label: str
    project_label: str
    collection_label: str

    def update(self, client) -> None:
        """Updates the snapshot status"""
        snapshot = client.get(f"/snapshot/projects/{self.parents.project}/snapshot/{self._id}")
        self.status = snapshot.status

    def is_final(self) -> bool:
        """Helper that indicates whether or not this is a terminal state"""
        return self.status.is_final()



    def to_series(self):
        return pd.Series(
            {
                "group_label": self.group_label,
                "project_label": self.project_label,
                "project_id": self.parents.project,
                "snapshot_id": self._id,
                "timestamp": self.format_timestamp(),
                "collection_label": self.collection_label,
                "status": self.status,
            }
        )

    def format_timestamp(self):
        """Get a formatted timestamp from a snapshot"""
        return datetime.strftime(self.created, RECORD_TIMESTAMP_FORMAT)


def string_matches_id(string: str) -> bool:
    """determines if a string matches the flywheel ID format
    Args:
        string: the string to check
    Returns:
        True if the string matches the flywheel ID format, False otherwise
    """
    return True if re.fullmatch(CONTAINER_ID_FORMAT, string) else False


def make_snapshot(client: FWClient, project_id: str) -> str:
    """makes a snapshot on a project
    Args:
        client: a flywheel client
        project_id: the ID of the project to make a snapshot on
    Returns:
        the ID of the snapshot
    """
    log.debug(f"creating snapshot on {project_id}")
    response = client.post(f"/snapshot/projects/{project_id}/snapshots")
    return response["_id"]


def get_snapshot(client: FWClient, project_id: str, snapshot_id: str) -> dict:
    """gets a snapshot from a project
    Args:
        client: a flywheel client
        project_id: the ID of the project to get the snapshot from
        snapshot_id: the ID of the snapshot to get
    Returns:
        the snapshot dict response from the flywheel API if found, None otherwise
    """
    endpoint = f"/snapshot/projects/{project_id}/snapshots/{snapshot_id}"
    try:
        response = client.get(endpoint)
    except NotFound:
        log.error(f"Unable to find snapshot {snapshot_id} on project {project_id}")
        response = None
    return response

