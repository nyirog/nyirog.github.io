Title: Reflect go to dbus
Author: Nyirő, Gergő
Summary: Register standard go struct to dbus with the help of reflection
Date: 2021-02-05T19:42:00
Category: dbus
Tags: dbus, go

The [prop.go](https://github.com/godbus/dbus/blob/master/_examples/prop.go)
godbus example demonstrates how easy to register a dbus property from go and
access the changed value at update. But what if we require all our config data at
once when one of its property is changed?

We will look through how to register a native go struct to dbus as a map of
dbus properties and access the whole struct when any of its field is updated.

We will need two transformations to achieve our goal:

* Convert struct to a `map[string]interface{}`.
* Set struct field by its name from the dbus change.

# Struct to map

The godbus [prop.Prop](https://github.com/godbus/dbus/blob/master/prop/prop.go)
accepts any go value which has dbus equivalent type so we only have to convert
our struct to a map where the keys will be set from the field names.

This is quite straightforward with
[reflecttion](https://blog.golang.org/laws-of-reflection):

```go
func CreateStructMap(config interface{}) map[string]interface{} {
	var struct_map = make(map[string]interface{})

	config_value := reflect.ValueOf(config).Elem()
	config_type := config_value.Type()

	for i := 0; i < config_type.NumField(); i++ {
		field_type := config_type.Field(i)
		if strings.Title(field_type.Name) != field_type.Name {
			continue
		}

		struct_map[field_type.Name] = config_value.Field(i).Interface()
	}

	return struct_map
}
```

The only trick what we did is to skip the fields which are not capitalized
(private fields). The struct fields could have been exported to dbus by
[StructTag](https://golang.org/pkg/reflect/#example_StructTag_Lookup) but our
export-all-public-field strategy will be good enough for now.

# Set struct field by its name

The update of the struct from the `prop.Change` is more straightforward:

```go
func SetStructField(config interface{}, change *prop.Change) {
	config_value := reflect.ValueOf(config).Elem()
	config_value.FieldByName(change.Name).Set(reflect.ValueOf(change.Value))
}
```

Only two comments is required for the function above:

* We have to call the `Elem()` method on the `reflect.Value` because our struct
  will be passed as reference.
* The `change.Value` has to be wrapped into a `reflect.Value` so the general
  `Set()`  method can be used.

# Updatable interface

Our helper functions are quite easy to use but it is more general if we define an
interface above them:

```go
type Updatable interface {
	Update(*prop.Change) *dbus.Error

	CreatePropertyMap() map[string]interface{}
}
```

Let see how we can implement `Updatable` interface with a common struct:

```go
type Config struct {
	SomeInt    int32
	SomeString string
}

func (config *Config) Update(change *prop.Change) *dbus.Error {
	SetStructField(config, change)

	return nil
}

func (config *Config) CreatePropertyMap() map[string]interface{} {
	return CreateStructMap(config)
}
```

# Register to dbus

Only two helper functions are missing to finish our task. The first function creates
a `map[string]*prop.Prop` from our `map[string]interface`:

```go
func createProps(config Updatable) map[string]*prop.Prop {
	var props = make(map[string]*prop.Prop)

	for name, value := range config.CreatePropertyMap() {
		props[name] = &prop.Prop{
			value,
			true,
			prop.EmitTrue,
			config.Update,
		}
	}

	return props
}
```

And the second function exports our `map[string]*prop.Prop` to dbus:

```go
func CreateNode(conn *dbus.Conn, path dbus.ObjectPath, iface string, config Updatable) {
	propsSpec := map[string]map[string]*prop.Prop{
		iface: createProps(config),
	}
	props := prop.New(conn, path, propsSpec)
	node := &introspect.Node{
		Name: string(path),
		Interfaces: []introspect.Interface{
			introspect.IntrospectData,
			prop.IntrospectData,
			{
				Name:       iface,
				Properties: props.Introspection(iface),
			},
		},
	}
	conn.Export(introspect.NewIntrospectable(node), path,
		"org.freedesktop.DBus.Introspectable")
}
```

This last function is a simple copy from the `prop.go` example of godbus
(except createProps).


# Final form

We can put the pieces together to have a simple dbus application:

```go
package main

import (
	"fmt"
	"os"

	"github.com/nyirog/configd"

	"github.com/godbus/dbus/v5"
	"github.com/godbus/dbus/v5/prop"
)

type Config struct {
	SomeInt    int32
	SomeString string
}

func (config *Config) Update(change *prop.Change) *dbus.Error {
	configd.SetStructField(config, change)

	return nil
}

func (config *Config) CreatePropertyMap() map[string]interface{} {
	return configd.CreateStructMap(config)
}


func main() {
	config := Config{SomeInt: 42, SomeString: "egg"}

	conn, err := dbus.SessionBus()
	if err != nil {
		panic(err)
	}
	reply, err := conn.RequestName("org.configd",
		dbus.NameFlagDoNotQueue)
	if err != nil {
		panic(err)
	}
	if reply != dbus.RequestNameReplyPrimaryOwner {
		fmt.Fprintln(os.Stderr, "name already taken")
		os.Exit(1)
	}

	configd.CreateNode(conn, "/config", "org.configd.Config", &config)

	fmt.Println("Listening on org.configd /config ...")

	select {}
}
```

**Note:** Our helper function are imported from the
[configd](https://github.com/nyirog/configd) package.

# Validate our input

Since we have a standard go struct in our hands we can use the
[validator](https://pkg.go.dev/gopkg.in/go-playground/validator.v9) package to
validate our user input:

```go
package main

import (
    ...

	"gopkg.in/go-playground/validator.v9"
)

type Config struct {
	SomeInt    int32  `validate:"max=50"`
	SomeString string `validate:"len=3"`
}

func (config *Config) Update(change *prop.Change) *dbus.Error {
	configd.SetStructField(config, change)

	err := validate.Struct(config)
	if err != nil {
		return validationError(err.(validator.ValidationErrors))
	}

	fmt.Println("Update", change.Name, change.Value)
	return nil
}

func (config *Config) CreatePropertyMap() map[string]interface{} {
	return configd.CreateStructMap(config)
}

func validationError(err validator.ValidationErrors) *dbus.Error {
	body := make([]interface{}, len(err))
	for i, e := range err {
		body[i] = fmt.Sprintf(
			"%s[%s=%s] <> %v", e.Field(), e.Tag(), e.Param(), e.Value(),
		)
	}
    return dbus.NewError("org.freedesktop.DBus.Properties.Error.ValidationErrors", body)
}

var validate *validator.Validate

func main() {
	validate = validator.New()

    ...
}
```

You can find more example under the
[_example](https://github.com/nyirog/configd/tree/main/_example) directory of
the `configd` package.
