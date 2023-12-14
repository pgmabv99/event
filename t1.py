import uuid

from esdbclient import EventStoreDBClient, NewEvent, StreamState


# Construct EventStoreDBClient with an EventStoreDB URI. The
# connection string URI specifies that the client should
# connect to an "insecure" server running on port 2113.

client = EventStoreDBClient(
    uri="esdb://localhost:2113?Tls=false"
)


# Generate new events. Typically, domain events of different
# types are generated in a domain model, and then serialized
# into NewEvent objects. An aggregate ID may be used as the
# name of a stream in EventStoreDB.

stream_name1 = str(uuid.uuid4())
event1 = NewEvent(
    type='OrderCreated',
    data=b'{"order_number": "123456"}'
)
event2 = NewEvent(
    type='OrderSubmitted',
    data=b'{}'
)
event3 = NewEvent(
    type='OrderCancelled',
    data=b'{}'
)


# Append new events to a new stream. The value returned
# from the append_to_stream() method is the overall
# "commit position" in the database of the last new event
# recorded by this operation. The returned "commit position"
# may be used in a user interface to poll an eventually
# consistent event-processing component until it can
# present an up-to-date materialized view. New events are
# each allocated a "stream position", which is the next
# available position in the stream, starting from 0.

commit_position1 = client.append_to_stream(
    stream_name=stream_name1,
    current_version=StreamState.NO_STREAM,
    events=[event1, event2],
)

# Append events to an existing stream. The "current version"
# is the "stream position" of the last recorded event in a
# stream. We have recorded two new events, so the "current
# version" is 1. The exception 'WrongCurrentVersion' will be
# raised if an incorrect value is given.

commit_position2 = client.append_to_stream(
    stream_name=stream_name1,
    current_version=1,
    events=[event3],
)

# - allocated commit positions increase monotonically
assert commit_position2 > commit_position1


# Read events from a stream. This method returns a
# "read response" iterator, which returns recorded
# events. The iterator will stop when there are no
# more events to be returned.

read_response = client.read_stream(
    stream_name=stream_name1
)

# Iterate over "read response" to get recorded events.
# The recorded events may be deserialized to domain event
# objects of different types and used to reconstruct an
# aggregate in a domain model.
recorded_events = tuple(read_response)

# - stream 'stream_name1' now has three events
assert len(recorded_events) == 3

# - allocated stream positions are zero-based and gapless
assert recorded_events[0].stream_position == 0
assert recorded_events[1].stream_position == 1
assert recorded_events[2].stream_position == 2

# - event attribute values are recorded faithfully
assert recorded_events[0].type == "OrderCreated"
assert recorded_events[0].data == b'{"order_number": "123456"}'
assert recorded_events[0].id == event1.id

assert recorded_events[1].type == "OrderSubmitted"
assert recorded_events[1].data == b'{}'
assert recorded_events[1].id == event2.id

assert recorded_events[2].type == "OrderCancelled"
assert recorded_events[2].data == b'{}'
assert recorded_events[2].id == event3.id


# Start a catch-up subscription from last recorded position.
# This method returns a "catch-up subscription" iterator,
# which returns recorded events. The iterator will not stop
# when there are no more recorded events to be returned, but
# will block, and continue when further events are recorded.

catchup_subscription = client.subscribe_to_all()


# Iterate over the catch-up subscription. Process each recorded
# event in turn. Within an atomic database transaction, record
# the event's "commit position" along with any new state generated
# by processing the event. Use the component's last recorded commit
# position when restarting the catch-up subscription.

received_events = []
for event in catchup_subscription:
    received_events.append(event)

    if event.commit_position == commit_position2:
        # Break so we can continue with the example.
        break


# - events are received in the order they were recorded
assert received_events[-3].type == "OrderCreated"
assert received_events[-3].data == b'{"order_number": "123456"}'
assert received_events[-3].id == event1.id

assert received_events[-2].type == "OrderSubmitted"
assert received_events[-2].data == b'{}'
assert received_events[-2].id == event2.id

assert received_events[-1].type == "OrderCancelled"
assert received_events[-1].data == b'{}'
assert received_events[-1].id == event3.id


# Stop the catch-up subscription iterator.

catchup_subscription.stop()


# Close the client's gRPC connection.

client.close()