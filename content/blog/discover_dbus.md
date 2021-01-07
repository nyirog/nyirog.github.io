Title: Discover dbus
Author: Nyirő, Gergő
Summary: Discover dbus with dbus-send
Date: 2021-01-07T20:22:00
Category: dbus

In this guide we will discover dbus services with the
[dbus-send](https://dbus.freedesktop.org/doc/dbus-send.1.html) command. `dbus-send` may
not the most user friendly tool to introspect dbus services but we can learn
more about the dbus protocol in this way.

# List connections

As the first step we should list the connections on the session bus:

```text
$ dbus-send --session --dest=org.freedesktop.DBus --type=method_call --print-reply \
  /org/freedesktop/DBus org.freedesktop.DBus.ListNames

   array [
      string "org.freedesktop.DBus"
      string ":1.403"
      string "org.freedesktop.Notifications"
      string ":1.405"
      string "org.freedesktop.portal.Desktop"
      string "org.freedesktop.systemd1"
      string ":1.408"
      string "org.pulseaudio.Server"
      ...
   ]
```

This command requires some explanation: `dbus-send` call the `ListNames` method of
`/org/freedesktop/DBus` object at the `org.freedesktop.DBus` address. The `ListNames`
method is defined in the `org.freedesktop.DBus` interface that's why we wrote
`org.freedesktop.DBus.ListNames` at the end of the command.

The reply is the list of bus names on the session bus. You can see two kind of
bus names there: unique name (:1.403) and well-known name (org.pulseaudio.Server).
All the bus clients has a unique name but they can require well-known name, too.
Services usually has well known name for easier access.

You may ask why we have to write `org.freedesktop.DBus` so many times. The answer lies
in the components of dbus protocol: addresses, objects and interfaces.

## Address

The well-known name of a dbus client is only used in message routing. Other
features like [match
rule](https://dbus.freedesktop.org/doc/dbus-specification.html#message-bus-routing-match-rules)
uses only the unique name of the client. So the well-known name has to be
unique on the bus but it does not provide any further information about the
client behavior.

## Object

The name of the object can be used in match filters so it should be unique and
they usually follow the same naming convention as the well-known bus name:

```text
org.freedesktop.DBus -> /org/freedesktop/DBus
```

## Interface

The interfaces describes the methods, signals and properties of the dbus objects
they meant to be reusable so there are standard interfaces which are implemented
by most of the dbus objects. Because interfaces can be shared their name are unique
therefore the object specific interfaces starts with the well-known name of the
service. Such an interface is the `org.freedesktop.DBus` which contains the `ListNames`
method.

# Introspect

Let see what other methods are implemented by `/org/freedesktop/DBus`:

```text
$ dbus-send --session --dest=org.freedesktop.DBus --type=method_call --print-reply \
  /org/freedesktop/DBus org.freedesktop.DBus.Introspectable.Introspect

   string "<!DOCTYPE node PUBLIC "-//freedesktop//DTD D-BUS Object Introspection 1.0//EN" "http://www.freedesktop.org/standards/dbus/1.0/introspect.dtd">
<node>
  <interface name="org.freedesktop.DBus">
    <method name="RequestName">
      <arg direction="in" type="s"/>
      <arg direction="in" type="u"/>
      <arg direction="out" type="u"/>
    </method>
    <method name="ListNames">
      <arg direction="out" type="as"/>
    </method>
    ...
    <property name="Features" type="as" access="read">
      <annotation name="org.freedesktop.DBus.Property.EmitsChangedSignal" value="const"/>
    </property>
    <property name="Interfaces" type="as" access="read">
      <annotation name="org.freedesktop.DBus.Property.EmitsChangedSignal" value="const"/>
    </property>
    ...
    <signal name="NameAcquired">
      <arg type="s"/>
    </signal>
  </interface>
  <interface name="org.freedesktop.DBus.Properties">
    <method name="Get">
      <arg direction="in" type="s"/>
      <arg direction="in" type="s"/>
      <arg direction="out" type="v"/>
    </method>
    <method name="GetAll">
      <arg direction="in" type="s"/>
      <arg direction="out" type="a{sv}"/>
    </method>
    <method name="Set">
      <arg direction="in" type="s"/>
      <arg direction="in" type="s"/>
      <arg direction="in" type="v"/>
    </method>
    <signal name="PropertiesChanged">
      <arg type="s" name="interface_name"/>
      <arg type="a{sv}" name="changed_properties"/>
      <arg type="as" name="invalidated_properties"/>
    </signal>
  </interface>
  <interface name="org.freedesktop.DBus.Introspectable">
    <method name="Introspect">
      <arg direction="out" type="s"/>
    </method>
  </interface>
  ...
</node>
"
```

The dbus objects can be introspected with the `Introspect` method of the
`org.freedesktop.DBus.Introspectable` interface. The
`org.freedesktop.DBus.Introspectable` is one of the [standard
interfaces](https://dbus.freedesktop.org/doc/dbus-specification.html#standard-interfaces)
which are implemented by all the dbus objects. The reply of the `Introspect` is
an xml document which is defined in the
[introspect.dtd](https://dbus.freedesktop.org/doc/dbus-specification.html#introspection-format).

## Method

The introspect xml document is quite readable alone without its specification.
For example the `RequestName` method has two arguments (`direction="in"`) a string (`type="s"`) and
a 32-bit unsigned integer (`type="u"`) and returns (`direction="out"`) a 32-bit unsigned
integer. You can read more about the type notation in the [dbus
overview](https://pythonhosted.org/txdbus/dbus_overview.html).

Let see how the `RequestName` method works:

```text
$ dbus-send --session --dest=org.freedesktop.DBus --type=method_call --print-reply \
  /org/freedesktop/DBus org.freedesktop.DBus.RequestName string:'foo.bar.baz' uint32:4

  uint32:1
```

The first argument is the requested name and the second argument is a flag
where `4` means `DBUS_NAME_FLAG_DO_NOT_QUEUE`. The other values of the flag
are described in the [bus
messages](https://dbus.freedesktop.org/doc/dbus-specification.html#message-bus-messages)
section of the dbus specification.

## Signal

Beside the return value the `/org/freedesktop/DBus` object will broadcast a
`org.freedesktop.DBus.NameAcquired` signal if the `RequestName` call succeeded.
This is a common pattern in dbus that some method call triggers a signal so an
observer client can match to the signals and collect the changes about the
other clients.

For development purposes the dbus messages can be monitored with `dbus-monitor`:

```text
$ dbus-monitor --session

signal time=1609972071.551809 sender=org.freedesktop.DBus -> destination=:1.572 serial=2 path=/org/freedesktop/DBus; interface=org.freedesktop.DBus; member=NameAcquired
   string ":1.572"
method call time=1609972071.552236 sender=:1.572 -> destination=org.freedesktop.DBus serial=2 path=/org/freedesktop/DBus; interface=org.freedesktop.DBus; member=RequestName
   string "foo.bar.baz"
   uint32 4
signal time=1609972071.552288 sender=org.freedesktop.DBus -> destination=(null destination) serial=45 path=/org/freedesktop/DBus; interface=org.freedesktop.DBus; member=NameOwnerChanged
   string "foo.bar.baz"
   string ""
   string ":1.572"
signal time=1609972071.552354 sender=org.freedesktop.DBus -> destination=:1.572 serial=3 path=/org/freedesktop/DBus; interface=org.freedesktop.DBus; member=NameAcquired
   string "foo.bar.baz"
method return time=1609972071.552387 sender=org.freedesktop.DBus -> destination=:1.572 serial=4 reply_serial=2
   uint32 1
signal time=1609972071.553096 sender=org.freedesktop.DBus -> destination=:1.572 serial=9 path=/org/freedesktop/DBus; interface=org.freedesktop.DBus; member=NameLost
   string "foo.bar.baz"
signal time=1609972071.553164 sender=org.freedesktop.DBus -> destination=(null destination) serial=46 path=/org/freedesktop/DBus; interface=org.freedesktop.DBus; member=NameOwnerChanged
   string "foo.bar.baz"
   string ":1.572"
   string ""
signal time=1609972071.553227 sender=org.freedesktop.DBus -> destination=:1.572 serial=10 path=/org/freedesktop/DBus; interface=org.freedesktop.DBus; member=NameLost
   string ":1.572"
```

From these messages above you can read the story of our short lived connection:

* Our client gets the :1.572 unique name.
* Our client requests the "foo.bar.baz" well-known name without queuing (4).
* `NameOwnerChanged` signal says that our client got the "foo.bar.baz" well-known name.
* `NameAcquired` signal says that "foo.bar.baz" name is acquired.
* Our client closes the connection so there will be 2 `NameLost` signal:
  one for our unique name and one for our requested well-known name.
* Between the two `NameLost` signal a second `NameOwnerChanged` signal shows that the "foo.bar.baz" is free.

## Property

The `org.freedesktop.DBus` interface holds some properties (`Features`,
`Interface`) beside the methods and signals. The properties can be managed via
the `org.freedesktop.DBus.Properties` interface. Let start with the `Get` method:

```text
$ dbus-send --session --dest=org.freedesktop.DBus --type=method_call --print-reply \
  /org/freedesktop/DBus org.freedesktop.DBus.Properties.Get string:'org.freedesktop.DBus' string:'Features'

   variant       array [
         string "SystemdActivation"
      ]

```

The first argument of the `Get` method is the interface name
(`string:'org.freedesktop.DBus'`) and the second argument is the property name
(`string:'Features'`).

_Remark:_ In some cases the interface name can be empty string if the object has only one
interface with properties.

The `GetAll` method replies with all the properties in a dict:

```text
$ dbus-send --session --dest=org.freedesktop.DBus --type=method_call --print-reply \
  /org/freedesktop/DBus org.freedesktop.DBus.Properties.GetAll string:'org.freedesktop.DBus'

   array [
      dict entry(
         string "Features"
         variant             array [
               string "SystemdActivation"
            ]
      )
      dict entry(
         string "Interfaces"
         variant             array [
               string "org.freedesktop.DBus.Monitoring"
               string "org.freedesktop.DBus.Debug.Stats"
            ]
      )
   ]
```

The properties of `org.freedesktop.DBus` are read only (`access="read"`) so we
cannot try the `Set` method.

_Remark:_ A successful `Set` call would trigger a
`org.freedesktop.DBus.PropertiesChanged` signal just like the `RequestName` method did
with `NameAcquired` signal.

## Object names

We can introspect a dbus object but how could we find its name?

Short answer we can introspect that, too. Let see the objects of `org.pulseaudio.Server`

```text
$ dbus-send --session --dest=org.pulseaudio.Server --type=method_call --print-reply \
  / org.freedesktop.DBus.Introspectable.Introspect

   string "<!DOCTYPE node PUBLIC "-//freedesktop//DTD D-BUS Object Introspection 1.0//EN" "http://www.freedesktop.org/standards/dbus/1.0/introspect.dtd">
<node>
  <node name="org"/>
</node>
"
```

So the `/` object only contains a sub node `org`. Let see the next level:

```text
$ dbus-send --session --dest=org.pulseaudio.Server --type=method_call --print-reply \
  /org org.freedesktop.DBus.Introspectable.Introspect

   string "<!DOCTYPE node PUBLIC "-//freedesktop//DTD D-BUS Object Introspection 1.0//EN" "http://www.freedesktop.org/standards/dbus/1.0/introspect.dtd">
<node>
  <node name="pulseaudio"/>
</node>
"
```

We can repeat this search until we find `server_lookup1`:

```text
$ dbus-send --session --dest=org.pulseaudio.Server --type=method_call --print-reply \
  /org/pulseaudio/server_lookup1 org.freedesktop.DBus.Introspectable.Introspect

   string "<!DOCTYPE node PUBLIC "-//freedesktop//DTD D-BUS Object Introspection 1.0//EN" "http://www.freedesktop.org/standards/dbus/1.0/introspect.dtd">
<node> <!-- If you are looking for documentation make sure to check out
      http://www.freedesktop.org/wiki/Software/PulseAudio/Documentation/Developer/Clients/DBus/ -->
 <interface name="org.PulseAudio.ServerLookup1">
  <property name="Address" type="s" access="read"/>
 </interface>
 ...
</node>
"
```

_Remark:_ The number in the object name (server_lookup**1**) is usually used
for API versioning (you should not search for multiple servers).

# Epilogue

This command can be applied to the system bus as well. Only the `--system`
option has to be used instead of `--session`.

Now you can discover the `system` and `session` buses on your machine without
any fancy GUI.
