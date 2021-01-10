Title: Register dbus service
Author: Nyirő, Gergő
Summary: Register a dbus system service with systemd
Date: 2021-01-10T19:12:00
Category: dbus
Tags: dbus, systemd

The promise of dbus is to eliminate the need of an init system by starting
the services on demand. In this guide we will walk through how to register
a simple service on the system bus and manage it via systemd.

**Remarks:**

* The guide assumes that `git` and `go` programs are already installed
  on your machine.
* The well-known name of the dbus client will be referred as `bus name`.

# Start a dbus service

We will use an example code from [godbus] as a dbus service.

```text
$ git clone https://github.com/godbus/dbus
```

We will use the latest release (`v5.0.3`) to avoid inconsistency:

```text
$ cd dbus
$ git checkout v5.0.3
```

`go` programs can be executed with the `go run` command:

```text
$ go run _examples/server.go 
Listening on com.github.guelfey.Demo / /com/github/guelfey/Demo ...
```

Let see what `/com/github/guelfey/Demo` object can do:

```text
$ dbus-send --session --dest=com.github.guelfey.Demo \
  --type=method_call --print-reply \
  /com/github/guelfey/Demo org.freedesktop.DBus.Introspectable.Introspect

   string "
<node>
	<interface name="com.github.guelfey.Demo">
		<method name="Foo">
			<arg direction="out" type="s"/>
		</method>
	</interface>
	<interface name="org.freedesktop.DBus.Introspectable">
		<method name="Introspect">
			<arg name="out" direction="out" type="s"/>
		</method>
	</interface>
</node> "
```

We have a `Foo` method in the `com.github.guelfey.Demo` interface. Let see what
`Foo` method does:

```text
$ dbus-send --session --dest=com.github.guelfey.Demo \
  --type=method_call --print-reply \
  /com/github/guelfey/Demo com.github.guelfey.Demo.Foo

   string "Bar!"
```

Nice, but we used `session` bus all along. How about the `system` bus?

# System bus

Change our example program to connect to the `system` bus:

```diff
diff --git a/_examples/server.go b/_examples/server.go
index 0f4ee32..76d5151 100644
--- a/_examples/server.go
+++ b/_examples/server.go
@@ -24,7 +24,7 @@ func (f foo) Foo() (string, *dbus.Error) {
 }

 func main() {
-       conn, err := dbus.SessionBus()
+       conn, err := dbus.SystemBus()
        if err != nil {
                panic(err)
        }
```

Start our service again:

```text
$ go run _examples/server.go
panic: Connection ":1.102" is not allowed to own the service "com.github.guelfey.Demo" due to security policies in the configuration file

goroutine 1 [running]:
main.main()
	/home/nyirogergo/workspace/dbus/_examples/server.go:40 +0x238
exit status 2
```

## System bus policy 

Arbitrary dbus client cannot acquire names on `system` bus. We have to create a policy file
to register the name of our server. Lucky for us the `Integrating system services` section
of the [dbus-daemon documentation](https://dbus.freedesktop.org/doc/dbus-daemon.1.html)
defines a minimal policy file:

```xml
<!-- /usr/share/dbus-1/system.d/com.github.guelfey.Demo.conf -->
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE busconfig PUBLIC
 "-//freedesktop//DTD D-BUS Bus Configuration 1.0//EN"
 "http://www.freedesktop.org/standards/dbus/1.0/busconfig.dtd">
<busconfig>
  <policy user="${USER}">
    <allow own="com.github.guelfey.Demo"/>
  </policy>

  <policy context="default">
    <allow send_destination="com.github.guelfey.Demo"/>
  </policy>
</busconfig>
```

The policy should be saved as
`/usr/share/dbus-1/system.d/com.github.guelfey.Demo.conf` so the
`com.github.guelfey.Demo` name will be available for `${USER}`. The `${USER}` has
to be replaced with a local username which can be yours too. More details about
the bus policy can be read in the [dbus-daemon] and [polkit] documentations.

**Remark:** The `/usr/share/dbus-1/system.d` directory does not refer to systemd, this
directory only contains the policies of the `system` bus configuration
(`/usr/share/dbus-1/system.conf`).

We can start our example server again:

```text
$ go run _examples/server.go
Listening on com.github.guelfey.Demo / /com/github/guelfey/Demo ...
```

The `Foo` method is available on the `system` bus:

```
$ dbus-send --system --dest=com.github.guelfey.Demo \
  --type=method_call --print-reply \
  /com/github/guelfey/Demo com.github.guelfey.Demo.Foo

   string "Bar!"
```

# Dbus service

Until now we could not refer our example server as dbus service because we
started it by hand. However it is quite straightforward to register our server
into dbus.

At first we compile our example server so it can be referred more easily:

```text
$ go build -o /tmp/dbus-demo-server _example/server.go
```

## Register service

The `dbus-daemon` scan the `/usr/share/dbus-1/system-services` for `system` services.
We should create a simple service file there. The service file has to be
named after bus name of the service.

```ini
# /usr/share/dbus-1/system-services/com.github.guelfey.Demo.service

[D-BUS Service]
Name=com.github.guelfey.Demo
User=${USER}
Exec=/tmp/dbus-demo-server
```

**Remark:** `${USER}` should be replaced with username which is used in the policy file.

## List activate able services

We can check our service configuration by the `ListActivatableNames` method:

```text
$ dbus-send --system --dest=org.freedesktop.DBus \
  --type=method_call --print-reply \
  /org/freedektop/DBus org.freedesktop.DBus.ListActivatableNames

   array [
      string "org.freedesktop.DBus"
      string "org.freedesktop.login1"
      ...
      string "com.github.guelfey.Demo"
   ]
```

It seems alright, let call our famous `Foo` method:

```text
$ dbus-send --system --dest=com.github.guelfey.Demo \
  --type=method_call --print-reply \
  /com/github/guelfey/Demo com.github.guelfey.Demo.Foo

   string "Bar!"
```

## Manage dbus services

It is quite easy, but how can I stop or restart our service?

Dbus services are regular processes so we only have to know their PIDs, which
can be queried with the `GetConnectionUnixProcessID` method:

```text
$ dbus-send --system --dest=org.freedesktop.DBus \
  --type=method_call --print-reply \
  /org/freedektop/DBus org.freedesktop.DBus.GetConnectionUnixProcessID \
  string:'com.github.guelfey.Demo'

   uint32 7909
```

We can stop our example service with a `SIGINT` signal:

```text
$ kill -SIGINT 7909
```

We can ensure that our example service is stopped:

```text
$ dbus-send --system --dest=org.freedesktop.DBus \
  --type=method_call --print-reply \
  /org/freedektop/DBus org.freedesktop.DBus.GetConnectionUnixProcessID \
  string:'com.github.guelfey.Demo'

Error org.freedesktop.DBus.Error.NameHasNoOwner: Could not get PID of name 'com.github.guelfey.Demo': no such name
```

# Systemd service

The `GetConnectionUnixProcessID` exposes the process of the dbus service but it
is not an administrator friendly way to manage services. Lucky for us dbus
services can be managed with systemd so we don't have to query their PIDs.

## Register service

Only a `SystemdService` option has to be set in the dbus service file to ask
`dbus-daemon` to start our service with systemd:

```ini
# /usr/share/dbus-1/system-services/com.github.guelfey.Demo.service

[D-BUS Service]
Name=com.github.guelfey.Demo
Exec=/bin/false
SystemdService=dbus-demo
```

As you can see from the dbus service file above the `User` option is left to
systemd and the `Exec` option is overwritten with `/bin/false` so the `Exec`
would fail if there is no `SystemdService`.

The systemd service file of the referred `dbus-demo` service should look like this:

```ini
# /usr/lib/systemd/system/dbus-demo.service

[Unit]
Description=Simple dbus server example
[Service]
Type=dbus
BusName=com.github.guelfey.Demo
ExecStart=/tmp/dbus-demo-server
User=${USER}
```

This systemd service above will start `/tmp/dbus-demo-server` at the first dbus
message as `${USER}` (you have to replace it with a real username). Systemd use
the `BusName` option in the status check of our example server. Systemd
consider the service active if the started process acquires the
`com.github.guelfey.Demo` `BusName`.

Finally a `daemon-reload` command has to be called to register our systemd service:

```text
$ sudo systemctl daemon-reload
```

At this stage our systemd service is inactive:

```text
$ systemctl status dbus-demo
● dbus-demo.service - Simple dbus server example
     Loaded: loaded (/usr/lib/systemd/system/dbus-demo.service; disabled; vendor preset: disabled)
     Active: inactive (dead)
```

It will be activated by the first dbus message:

```text
$ dbus-send --system --dest=com.github.guelfey.Demo \
  --type=method_call --print-reply \
  /com/github/guelfey/Demo com.github.guelfey.Demo.Foo

   string "Bar!"
```

```text
$ systemctl status dbus-demo
● dbus-demo.service - Simple dbus server example
     Loaded: loaded (/usr/lib/systemd/system/dbus-demo.service; disabled; vendor preset: disabled)
     Active: active (running) since Sun 2021-01-10 16:44:42 CET; 12s ago
   Main PID: 8500 (dbus-demo-serve)
      Tasks: 6 (limit: 38345)
     Memory: 1.2M
     CGroup: /system.slice/dbus-demo.service
             └─8500 /usr/bin/dbus-demo-server

```

We can check that `systemd` and `dbus-daemon` use the same process (PID=8500):

```text
$ dbus-send --system --dest=org.freedesktop.DBus \
  --type=method_call --print-reply \
  /org/freedektop/DBus org.freedesktop.DBus.GetConnectionUnixProcessID \
  string:'com.github.guelfey.Demo'

   uint32 8500
```

# Epilogue

You have to remember that neither `dbus-daemon` or `systemd` acquire bus name for your
server. The bus name has to be acquired by your server.

We did not use any policy for our example server, but authorization is key
point of dbus services. You should use [polkit] or a proper bus policy for your
dbus services.

[dbus-daemon]: https://dbus.freedesktop.org/doc/dbus-daemon.1.html
[polkit]: https://www.freedesktop.org/software/polkit/docs/latest/polkit.8.html
[godbus]: https://github.com/godbus/dbus
