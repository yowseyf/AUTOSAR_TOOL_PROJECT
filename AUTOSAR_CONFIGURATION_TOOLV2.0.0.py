import json

# Software Composition Classes
class SoftwareComposition:
    """
    Represents a Software Composition in AUTOSAR, containing multiple Software Components.
    """
    def __init__(self, name):
        self.name = name
        self.software_components = []  # List to hold SoftwareComponent objects

    def add_software_component(self, swc):
        """
        Adds a Software Component to the composition.
        Ensures no duplicate component names exist.
        """
        if any(component.name == swc.name for component in self.software_components):
            raise ValueError(f"A SoftwareComponent with the name '{swc.name}' already exists.")
        self.software_components.append(swc)

    def list_software_components(self):
        """Returns a list of the names of all Software Components in the composition."""
        return [component.name for component in self.software_components]

    def validate_composition(self):
        """Validate the entire software composition."""
        errors = []

        # Validate each software component
        for component in self.software_components:
            errors.extend(component.validate_component())

        # Validate port connections
        errors.extend(self.validate_port_connections())

        # Validate topology
        errors.extend(self.validate_topology())

        return errors

    def validate_port_connections(self):
        """Ensure that every sender port has a matching receiver."""
        errors = []
        all_ports = []

        for component in self.software_components:
            for port in component.ports.values():
                all_ports.append((component.name, port))

        sender_ports = [p for p in all_ports if p[1].port_type == "sender"]
        receiver_ports = [p for p in all_ports if p[1].port_type == "receiver"]

        unmatched_senders = [p for p in sender_ports if not any(p[1].name == r[1].name for r in receiver_ports)]
        unmatched_receivers = [p for p in receiver_ports if not any(p[1].name == s[1].name for s in sender_ports)]

        for sender in unmatched_senders:
            errors.append(f"Sender port '{sender[1].name}' in component '{sender[0]}' has no matching receiver.")

        for receiver in unmatched_receivers:
            errors.append(f"Receiver port '{receiver[1].name}' in component '{receiver[0]}' has no matching sender.")

        return errors

    def validate_topology(self):
        """Ensure there are no circular dependencies."""
        errors = []

        visited = set()
        stack = []

        def visit(component):
            if component.name in stack:
                errors.append(f"Circular dependency detected involving component '{component.name}'.")
                return
            if component.name not in visited:
                stack.append(component.name)
                visited.add(component.name)
                for port in component.ports.values():
                    connected_components = [c for c in self.software_components if port.name in c.ports]
                    for connected_component in connected_components:
                        visit(connected_component)
                stack.pop()

        for component in self.software_components:
            visit(component)

        return errors

    def to_json(self):
        """Convert the software composition to JSON format."""
        composition_data = {
            "composition_name": self.name,
            "components": []
        }
        for component in self.software_components:
            component_data = {
                "name": component.name,
                "type": component.component_type,
                "ports": [
                    {"name": port.name, "type": port.port_type} for port in component.ports.values()
                ],
                "runnables": [
                    {
                        "name": runnable.name,
                        "trigger": runnable.trigger,
                        "period": runnable.period if runnable.trigger == "periodic" else None
                    } for runnable in component.runnables
                ],
                "interfaces": [
                    {
                        "name": interface.name,
                        "type": interface.interface_type,
                        "associated_ports": [port.name for port in interface.associated_port],
                        "data_elements": [
                            {"name": data_element.name, "type": data_element.DataType}
                            for data_element in interface.data_elements
                        ]
                    } for interface in component.interfaces
                ]
            }
            composition_data["components"].append(component_data)
        return composition_data

    def __str__(self):
        output = f"SOFTWARE Composition: {self.name}\n"
        for idx, component in enumerate(self.software_components, start=1):
            output += f"--Software Component {idx}: {component.name} (Type: {component.component_type})\n"
            output += component.detailed_str()
        return output


class SoftwareComponent:
    """
    Represents a Software Component in AUTOSAR, containing ports, runnables, and interfaces.
    """
    def __init__(self, name, component_type):
        self.name = name
        self.component_type = component_type  # Type of the component (e.g., "Sensor", "Controller")
        self.runnables = []  # List of Runnable objects
        self.ports = {}  # Dictionary to map port names to Port objects for efficient lookup
        self.interfaces = []  # List of Interface objects associated with this component

    def add_runnable(self, runnable):
        """Adds a Runnable to the component."""
        if not isinstance(runnable, Runnable):
            raise TypeError("Expected a Runnable object.")
        if any(r.name == runnable.name for r in self.runnables):
            raise ValueError(f"Runnable with the name '{runnable.name}' already exists in component '{self.name}'.")
        self.runnables.append(runnable)

    def add_port(self, port):
        """Adds a Port to the component."""
        if not isinstance(port, Port):
            raise TypeError("Expected a Port object.")
        if port.name in self.ports:
            raise ValueError(f"Port with the name '{port.name}' already exists in component '{self.name}'.")
        self.ports[port.name] = port

    def add_interface(self, interface, all_ports):
        """Associates an Interface with specified ports."""
        for port_name in all_ports:
            if port_name in self.ports:
                interface.associated_port.append(self.ports[port_name])
            else:
                raise ValueError(f"No port named '{port_name}' found for component '{self.name}'.")
        self.interfaces.append(interface)

    def validate_component(self):
        """Validate the individual software component."""
        errors = []

        # Check for missing ports
        if not self.ports:
            errors.append(f"Component '{self.name}' has no ports defined.")

        # Check for duplicate port names
        if len(self.ports) != len(set(self.ports.keys())):
            errors.append(f"Duplicate port names found in component '{self.name}'.")

        # Validate runnables
        for runnable in self.runnables:
            if runnable.trigger == "periodic" and runnable.period is None:
                errors.append(f"Runnable '{runnable.name}' in component '{self.name}' is periodic but has no period defined.")

        return errors

    def detailed_str(self):
        output = "---Ports Associated:\n"
        if self.ports:
            for port in self.ports.values():
                output += f"----{port.name} (Type: {port.port_type})\n"
        else:
            output += "----No ports associated.\n"

        output += "---Runnables Associated:\n"
        if self.runnables:
            for runnable in self.runnables:
                output += f"----{runnable.name} (Trigger: {runnable.trigger}, Period: {runnable.period if runnable.trigger == 'periodic' else 'N/A'})\n"
        else:
            output += "----No runnables associated.\n"

        output += "---Interfaces Associated:\n"
        if self.interfaces:
            displayed_interfaces = set()  # To track already displayed interfaces
            for interface in self.interfaces:
                if interface.name not in displayed_interfaces:
                    displayed_interfaces.add(interface.name)
                    associated_ports = ", ".join([port.name for port in interface.associated_port])
                    output += f"----{interface.name} (Type: {interface.interface_type}, Associated with ports: {associated_ports})\n"
                    # Add Data Elements associated with this interface
                    if interface.data_elements:
                        output += "------Data Elements:\n"
                        for data_element in interface.data_elements:
                            output += f"-------{data_element.name} (Type: {data_element.DataType})\n"
                    else:
                        output += "------No data elements associated.\n"
        else:
            output += "----No interfaces associated.\n"

        return output


class Runnable:
    """
    Represents a Runnable, which is a task or function executed by the component.
    """
    def __init__(self, name, trigger="event-based", period=None):
        self.name = name
        self.trigger = trigger  # Trigger type: "event-based" or "periodic"
        self.period = period  # Period in milliseconds (only for periodic triggers)

    def __str__(self):
        period_info = f", period={self.period}" if self.trigger == "periodic" else ""
        return f"Runnable(name={self.name}, trigger={self.trigger}{period_info})"


class Port:
    """
    Represents a Port for communication in AUTOSAR.
    """
    def __init__(self, name, port_type):
        self.name = name
        self.port_type = port_type  # Port type: "sender" or "receiver"

    def __str__(self):
        return f"Port(name={self.name}, type={self.port_type})"


class Interface:
    """
    Represents an Interface in AUTOSAR, associated with one or more ports.
    """
    def __init__(self, name, interface_type):
        self.name = name
        self.interface_type = interface_type  # Interface type: "clientServer" or "senderReceiver"
        self.associated_port = []  # List of associated Port objects
        self.data_elements = []  # List of DataElement objects associated with the interface

    def add_data_element(self, data_element):
        """Adds a Data Element to the interface."""
        self.data_elements.append(data_element)


class DataElement:
    def __init__(self, name, DataType):
        self.name = name
        self.DataType = DataType

    def __str__(self):
        return f"DataElement(name={self.name}, type={self.DataType})"


# Interactive Configuration Function
def interactive_configuration():
    """
    Interactive tool for creating and configuring an AUTOSAR Software Composition.
    """
    print("Welcome to the Software Configuration Tool!")

    # Create a Software Composition
    composition_name = input("Enter the name for your software composition: ")
    composition = SoftwareComposition(composition_name)

    while True:
        try:
            # Add a Software Component
            add_component = input("Would you like to add a Software Component (yes/no)? ").lower()
            if add_component == "no":
                break

            component_name = input("Enter the name of the Software Component: ")
            if component_name in composition.list_software_components():
                print(f"Error: A Software Component with the name '{component_name}' already exists. Please choose a different name.")
                continue

            component_type = input("Enter the type of the Software Component (e.g., Sensor, Controller): ")
            component = SoftwareComponent(component_name, component_type)

            # Add Ports
            while True:
                add_port = input(f"Would you like to add a port to '{component_name}' (yes/no)? ").lower()
                if add_port == "no":
                    break
                port_name = input("Enter the port name: ")
                port_type = input("Enter the port type (sender/receiver): ")
                component.add_port(Port(port_name, port_type))

            # Add Interfaces
            while True:
                add_interface = input(f"Would you like to add an interface to '{component_name}' (yes/no)? ").lower()
                if add_interface == "no":
                    break
                interface_name = input("Enter the name of the Interface: ")
                interface_type = input("Enter the interface type (clientServer/senderReceiver): ")
                interface = Interface(interface_name, interface_type)

                # Associate the Interface with Ports
                while True:
                    associate = input(f"Associate this interface with existing ports (yes/no)? ").lower()
                    if associate == "no":
                        break
                    print(f"Available ports for '{component_name}':")
                    for port in component.ports.values():
                        print(f"- {port.name} (Type: {port.port_type})")
                    port_name = input("Enter the port name to associate: ")
                    if port_name in component.ports:
                        component.add_interface(interface, [port_name])
                    else:
                        print(f"Port '{port_name}' not found.")

                # Add Data Elements to Interface
                while True:
                    add_data_element = input(f"Would you like to add a data element to the interface '{interface_name}' (yes/no)? ").lower()
                    if add_data_element == "no":
                        break
                    data_element_name = input("Enter the name of the Data Element: ")
                    data_element_type = input("Enter the type of the Data Element (e.g., int, float, string): ")
                    interface.add_data_element(DataElement(data_element_name, data_element_type))
                component.interfaces.append(interface)

            # Add Runnables
            while True:
                add_runnable = input(f"Would you like to add a runnable to '{component_name}' (yes/no)? ").lower()
                if add_runnable == "no":
                    break
                runnable_name = input("Enter the name of the Runnable: ")
                trigger_type = input("Enter the trigger type (periodic/event-based): ")
                period = int(input("Enter the period (ms): ")) if trigger_type == "periodic" else None
                component.add_runnable(Runnable(runnable_name, trigger_type, period))

            # Add the component to the composition
            composition.add_software_component(component)

        except ValueError as ve:
            print(f"Error: {ve}")

    # Display the final configuration
    print("\nSoftware Composition Configuration:")
    print(composition)

    # Validate the composition
    validation_errors = composition.validate_composition()
    if validation_errors:
        print("\nValidation Errors:")
        for error in validation_errors:
            print(f"- {error}")
    else:
        print("\nConfiguration is valid.")

    # Ask user if they want to export to JSON
    export_json = input("Would you like to export the configuration to a JSON file (yes/no)? ").strip().lower()
    if export_json == 'yes':
        json_data = composition.to_json()
        json_file_name = input("Enter the filename for the JSON file (e.g., composition.json): ").strip()
        try:
            with open(json_file_name, 'w') as json_file:
                json.dump(json_data, json_file, indent=4)
            print(f"Configuration successfully exported to '{json_file_name}'.")
        except Exception as e:
            print(f"Error while exporting JSON: {e}")
    else:
        print("JSON export skipped.")


# Run the interactive tool
interactive_configuration()
