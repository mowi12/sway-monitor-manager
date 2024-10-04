#!/usr/bin/python3

import argparse
import subprocess
import json
import sys
import inquirer
import os

# Argument parser
parser = argparse.ArgumentParser(description="Monitor Manager for Sway")
args = parser.parse_args()

WORKSPACES_FILE = "/home/mwieland/.config/sway/workspaces.json"


def enable_monitor(monitor_name):
    print(f"Enabling monitor: {monitor_name}")
    subprocess.run(["swaymsg", "output", monitor_name, "enable"], check=True)


def disable_monitor(monitor_name):
    print(f"Disabling monitor: {monitor_name}")
    subprocess.run(["swaymsg", "output", monitor_name, "disable"], check=True)


def set_rotation(output_name, rotation):
    print(f"Setting rotation of {output_name} to {rotation}")
    subprocess.run(
        ["swaymsg", "output", output_name, "transform", rotation], check=True
    )


def set_position(output_name, x, y):
    print(f"Setting position of {output_name} to ({x}, {y})")
    subprocess.run(
        ["swaymsg", "output", output_name, "position", str(x), str(y)], check=True
    )


def load_workspaces():
    if not os.path.exists(WORKSPACES_FILE):
        print(1)
        return {"workspaces": []}
    try:
        with open(WORKSPACES_FILE, "r") as f:
            print(2)
            return json.load(f)
    except json.JSONDecodeError:
        print("Error parsing workspaces.json.")
        return {"workspaces": []}


def save_workspaces(workspaces_data):
    with open(WORKSPACES_FILE, "w") as f:
        json.dump(workspaces_data, f, indent=4)
    print(f"Workspaces saved to {WORKSPACES_FILE}.")


def menu():
    while True:
        question = [
            inquirer.List(
                "mode",
                message="What do you want to do?",
                choices=["Manage Monitors", "Manage Workspaces", "Exit"],
            )
        ]
        answer = inquirer.prompt(question)

        if not answer:
            continue

        if answer["mode"] == "Manage Monitors":
            manage_monitors()
        elif answer["mode"] == "Manage Workspaces":
            manage_workspaces_menu()
        elif answer["mode"] == "Exit":
            sys.exit()


def manage_monitors():
    try:
        monitors_data = json.loads(
            subprocess.run(
                ["swaymsg", "-t", "get_outputs"], capture_output=True, text=True
            ).stdout
        )
    except json.JSONDecodeError:
        print("Failed to retrieve monitor information.")
        return

    if not monitors_data:
        print("No monitors found.")
        return

    choices = []
    monitor_map = {}

    for monitor in monitors_data:
        output_name = monitor["name"]
        make = monitor.get("make", "").strip()
        model = monitor.get("model", "").strip()
        serial = monitor.get("serial", "").strip()
        description = f"{make} {model} {serial}".strip()
        active = monitor["active"]
        transform = monitor.get("transform", "normal")
        position = monitor.get("rect", {"x": 0, "y": 0})
        x = position.get("x", 0)
        y = position.get("y", 0)

        monitor_info = f"{description} ({output_name}) - {active}, rot: {transform}, pos: ({x}, {y})"
        choices.append(monitor_info)
        monitor_map[monitor_info] = monitor

    question = [
        inquirer.Checkbox(
            "monitors",
            message="Select monitors to manage:",
            choices=choices,
        )
    ]
    answer = inquirer.prompt(question)

    if answer is None or not answer["monitors"]:
        print("No monitors selected.")
        return

    for monitor_info in answer["monitors"]:
        monitor = monitor_map[monitor_info]
        output_name = monitor["name"]

        # Ask if the user wants to enable or disable the monitor
        state_question = [
            inquirer.List(
                "state",
                message=f"Do you want to enable or disable {monitor_info}?",
                choices=["No Change", "Enable", "Disable"],
            )
        ]
        state_answer = inquirer.prompt(state_question)
        if state_answer is None:
            continue
        state_choice = state_answer["state"]

        # Ask if the user wants to set rotation
        rotation_question = [
            inquirer.List(
                "rotation",
                message=f"Set rotation for {monitor_info}:",
                choices=[
                    "No Change",
                    "normal",
                    "90",
                    "180",
                    "270",
                    "flipped",
                    "flipped-90",
                    "flipped-180",
                    "flipped-270",
                ],
            )
        ]
        rotation_answer = inquirer.prompt(rotation_question)
        if rotation_answer is None:
            continue
        rotation_choice = rotation_answer["rotation"]

        # Ask if the user wants to set position
        position_question = [
            inquirer.Text(
                "position",
                message=f"Enter position for {monitor_info} in format x,y (e.g., 0,0) or leave empty for no change:",
            )
        ]
        position_answer = inquirer.prompt(position_question)
        if position_answer is not None:
            position_input = position_answer["position"].strip()
            if position_input:
                try:
                    x_str, y_str = position_input.split(",")
                    x = int(x_str.strip())
                    y = int(y_str.strip())
                except ValueError:
                    print("Invalid position format. Skipping position change.")
                    x = None
                    y = None
            else:
                x = None
                y = None
        else:
            x = None
            y = None

        # Apply the changes
        if state_choice == "Enable":
            enable_monitor(output_name)
        elif state_choice == "Disable":
            disable_monitor(output_name)

        if rotation_choice != "No Change":
            set_rotation(output_name, rotation_choice)

        if x is not None and y is not None:
            set_position(output_name, x, y)


def manage_workspaces_menu():
    while True:
        question = [
            inquirer.List(
                "workspace_mode",
                message="Workspace Management Options:",
                choices=[
                    "Activate a Workspace",
                    "Create a New Workspace",
                    "Create Current Settings as Workspace",
                    "Delete a Workspace",
                    "Back to Main Menu",
                ],
            )
        ]
        answer = inquirer.prompt(question)

        if not answer:
            continue

        mode = answer["workspace_mode"]

        if mode == "Activate a Workspace":
            activate_workspace()
        elif mode == "Create a New Workspace":
            create_new_workspace()
        elif mode == "Create Current Settings as Workspace":
            create_current_as_workspace()
        elif mode == "Delete a Workspace":
            delete_workspace()
        elif mode == "Back to Main Menu":
            break


def activate_workspace():
    workspaces_data = load_workspaces()

    if not workspaces_data.get("workspaces"):
        print("No workspaces found in workspaces.json.")
        return

    workspace_names = [ws["name"] for ws in workspaces_data["workspaces"]]

    question = [
        inquirer.List(
            "workspace",
            message="Select a workspace to activate:",
            choices=workspace_names,
        )
    ]
    answer = inquirer.prompt(question)
    if answer is None:
        return
    selected_workspace_name = answer["workspace"]

    # Find the selected workspace configuration
    selected_workspace = next(
        (
            ws
            for ws in workspaces_data["workspaces"]
            if ws["name"] == selected_workspace_name
        ),
        None,
    )

    if selected_workspace is None:
        print("Workspace not found.")
        return

    # Get current monitors data
    try:
        monitors_data = json.loads(
            subprocess.run(
                ["swaymsg", "-t", "get_outputs"], capture_output=True, text=True
            ).stdout
        )
    except json.JSONDecodeError:
        print("Failed to retrieve monitor information.")
        return

    if not monitors_data:
        print("No monitors found.")
        return

    # Build a mapping from description to output_name
    description_to_output = {}
    for monitor in monitors_data:
        output_name = monitor["name"]
        make = monitor.get("make", "").strip()
        model = monitor.get("model", "").strip()
        serial = monitor.get("serial", "").strip()
        description = f"{make} {model} {serial}".strip()
        description_to_output[description] = output_name

    # Collect all output names from the workspace
    workspace_output_names = []
    for monitor_config in selected_workspace["monitors"]:
        description = monitor_config["description"]
        output_name = description_to_output.get(description)
        if output_name:
            workspace_output_names.append(output_name)

    # **Deactivate monitors not in the workspace**
    all_current_outputs = {monitor["name"] for monitor in monitors_data}
    workspace_outputs_set = set(workspace_output_names)
    monitors_to_disable = all_current_outputs - workspace_outputs_set

    for output in monitors_to_disable:
        disable_monitor(output)

    # Apply the workspace's monitor configurations
    for monitor_config in selected_workspace["monitors"]:
        description = monitor_config["description"]
        state = monitor_config.get("state", "enable")
        transform = monitor_config.get("transform", None)
        position = monitor_config.get("position", {"x": 0, "y": 0})
        x = position.get("x", 0)
        y = position.get("y", 0)

        output_name = description_to_output.get(description)
        if not output_name:
            print(f"Monitor with description '{description}' not found.")
            continue

        if state == "enable":
            enable_monitor(output_name)
        elif state == "disable":
            disable_monitor(output_name)

        if transform:
            set_rotation(output_name, transform)

        if x is not None and y is not None:
            set_position(output_name, x, y)


def create_new_workspace():
    workspaces_data = load_workspaces()

    # Prompt for workspace name
    workspace_name_question = [
        inquirer.Text(
            "name",
            message="Enter the name for the new workspace:",
        )
    ]
    workspace_name_answer = inquirer.prompt(workspace_name_question)
    if workspace_name_answer is None or not workspace_name_answer["name"].strip():
        print("Workspace name cannot be empty.")
        return

    workspace_name = workspace_name_answer["name"].strip()

    # Check for duplicate names
    if any(ws["name"] == workspace_name for ws in workspaces_data["workspaces"]):
        print(f"A workspace named '{workspace_name}' already exists.")
        return

    # Manage monitors for the new workspace
    print(f"\nConfiguring monitors for workspace '{workspace_name}':\n")
    try:
        monitors_data = json.loads(
            subprocess.run(
                ["swaymsg", "-t", "get_outputs"], capture_output=True, text=True
            ).stdout
        )
    except json.JSONDecodeError:
        print("Failed to retrieve monitor information.")
        return

    if not monitors_data:
        print("No monitors found.")
        return

    workspace_monitors = []

    for monitor in monitors_data:
        output_name = monitor["name"]
        make = monitor.get("make", "").strip()
        model = monitor.get("model", "").strip()
        serial = monitor.get("serial", "").strip()
        description = f"{make} {model} {serial}".strip()

        # Ask if the user wants to enable the monitor
        state_question = [
            inquirer.List(
                "state",
                message=f"Do you want to enable {description} ({output_name})?",
                choices=["Enable", "Disable"],
            )
        ]
        state_answer = inquirer.prompt(state_question)
        if state_answer is None:
            state_choice = "disable"
        else:
            state_choice = state_answer["state"].lower()

        if state_choice == "disable":
            continue

        # Ask if the user wants to set rotation
        rotation_question = [
            inquirer.List(
                "rotation",
                message=f"Set rotation for {description} ({output_name}):",
                choices=[
                    "normal",
                    "90",
                    "180",
                    "270",
                    "flipped",
                    "flipped-90",
                    "flipped-180",
                    "flipped-270",
                ],
                default=monitor.get("transform", "normal"),
            )
        ]
        rotation_answer = inquirer.prompt(rotation_question)
        if rotation_answer is None:
            rotation_choice = "normal"
        else:
            rotation_choice = rotation_answer["rotation"]

        # Ask if the user wants to set position
        position_question = [
            inquirer.Text(
                "position",
                message=f"Enter position for {description} ({output_name}) in format x,y (e.g., 0,0):",
                validate=lambda _, x: validate_position_input(x),
            )
        ]
        position_answer = inquirer.prompt(position_question)
        if position_answer is None or not position_answer["position"].strip():
            print("Position not set. Using default (0,0).")
            x = 0
            y = 0
        else:
            position_input = position_answer["position"].strip()
            try:
                x_str, y_str = position_input.split(",")
                x = int(x_str.strip())
                y = int(y_str.strip())
            except ValueError:
                print("Invalid position format. Using default (0,0).")
                x = 0
                y = 0

        workspace_monitors.append(
            {
                "description": description,
                "state": state_choice,
                "transform": rotation_choice,
                "position": {"x": x, "y": y},
            }
        )

    # Add the new workspace to the workspaces data
    workspaces_data["workspaces"].append(
        {
            "name": workspace_name,
            "monitors": workspace_monitors,
        }
    )

    save_workspaces(workspaces_data)
    print(f"Workspace '{workspace_name}' created successfully.")


def create_current_as_workspace():
    workspaces_data = load_workspaces()

    # Prompt for workspace name
    workspace_name_question = [
        inquirer.Text(
            "name",
            message="Enter the name for the new workspace based on current settings:",
        )
    ]
    workspace_name_answer = inquirer.prompt(workspace_name_question)
    if workspace_name_answer is None or not workspace_name_answer["name"].strip():
        print("Workspace name cannot be empty.")
        return

    workspace_name = workspace_name_answer["name"].strip()

    # Check for duplicate names
    if any(ws["name"] == workspace_name for ws in workspaces_data["workspaces"]):
        print(f"A workspace named '{workspace_name}' already exists.")
        return

    # Get current monitors data
    try:
        monitors_data = json.loads(
            subprocess.run(
                ["swaymsg", "-t", "get_outputs"], capture_output=True, text=True
            ).stdout
        )
    except json.JSONDecodeError:
        print("Failed to retrieve monitor information.")
        return

    if not monitors_data:
        print("No monitors found.")
        return

    workspace_monitors = []

    for monitor in monitors_data:
        output_name = monitor["name"]
        make = monitor.get("make", "").strip()
        model = monitor.get("model", "").strip()
        serial = monitor.get("serial", "").strip()
        description = f"{make} {model} {serial}".strip()
        state = "enable" if monitor["active"] else "disable"
        transform = monitor.get("transform", "normal")
        position = monitor.get("rect", {"x": 0, "y": 0})
        x = position.get("x", 0)
        y = position.get("y", 0)

        if state != "disable":
            workspace_monitors.append(
                {
                    "description": description,
                    "state": state,
                    "transform": transform,
                    "position": {"x": x, "y": y},
                }
            )

    # Add the new workspace to the workspaces data
    workspaces_data["workspaces"].append(
        {
            "name": workspace_name,
            "monitors": workspace_monitors,
        }
    )

    save_workspaces(workspaces_data)
    print(f"Workspace '{workspace_name}' created successfully from current settings.")


def delete_workspace():
    workspaces_data = load_workspaces()

    if not workspaces_data.get("workspaces"):
        print("No workspaces found in workspaces.json.")
        return

    workspace_names = [ws["name"] for ws in workspaces_data["workspaces"]]

    question = [
        inquirer.Checkbox(
            "workspaces",
            message="Select workspaces to delete:",
            choices=workspace_names,
        )
    ]
    answer = inquirer.prompt(question)

    if answer is None or not answer["workspaces"]:
        print("No workspaces selected for deletion.")
        return

    for ws_name in answer["workspaces"]:
        workspaces_data["workspaces"] = [
            ws for ws in workspaces_data["workspaces"] if ws["name"] != ws_name
        ]
        print(f"Workspace '{ws_name}' deleted.")

    save_workspaces(workspaces_data)


def validate_position_input(x):
    if not x.strip():
        return True  # Allow empty input
    try:
        x_str, y_str = x.split(",")
        int(x_str.strip())
        int(y_str.strip())
        return True
    except ValueError:
        return "Please enter position in format x,y where x and y are integers."


if __name__ == "__main__":
    menu()
