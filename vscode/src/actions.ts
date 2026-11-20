import * as vscode from "vscode";

interface Action {
  /** Short, so it fits the default sidebar width. */
  label: string;
  /** Only for something short like a key binding. */
  description?: string;
  /** The longer explanation, shown on hover. */
  tooltip: string;
  icon: string;
  command: string;
  /** Shown only in projects of this kind. */
  onlyFor?: "django";
}

interface Group {
  label: string;
  icon: string;
  actions: Action[];
}

export const GROUPS: Group[] = [
  {
    label: "Debug",
    icon: "debug-alt",
    actions: [
      {
        label: "Insert siren()",
        description: "Ctrl+Alt+S",
        tooltip: "Add siren() with the cursor inside, ready to type; or wrap the selection in siren(...)",
        icon: "add",
        command: "siren.insert",
      },
      {
        label: "Run Django server",
        tooltip:
          "Start manage.py runserver in a new terminal with Siren loaded: siren() in views, models and forms shows its value at the end of the line on each request",
        icon: "server-process",
        command: "siren.runDjango",
        onlyFor: "django",
      },
      {
        label: "Run current file",
        tooltip: "Run this Python file in a new terminal with Siren loaded; values show at the end of each line",
        icon: "play",
        command: "siren.runFile",
      },
      {
        label: "Enable everywhere",
        tooltip:
          "Make siren() work without an import in every program this project's Python runs, not only in VS Code terminals: servers, external terminals, scripts run by other tools",
        icon: "globe",
        command: "siren.enableEnvironment",
      },
      {
        label: "Captured values",
        tooltip: "Every value siren() has printed, in the Siren output channel",
        icon: "output",
        command: "siren.showOutput",
      },
      {
        label: "Clear inline values",
        tooltip: "Hide the values shown at the end of lines",
        icon: "clear-all",
        command: "siren.clearInlineValues",
      },
    ],
  },
  {
    label: "Clean up",
    icon: "trash",
    actions: [
      {
        label: "Remove from this file",
        tooltip: "Remove every siren() call and import from the current file",
        icon: "file",
        command: "siren.cleanFile",
      },
      {
        label: "Remove from workspace",
        tooltip: "Remove siren() calls from every file in the workspace, after showing which files will change",
        icon: "files",
        command: "siren.cleanWorkspace",
      },
    ],
  },
  {
    label: "Code",
    icon: "code",
    actions: [
      {
        label: "Check this file",
        tooltip: "Code quality for the current file: unused code, bare except, leftover breakpoints, TODOs, complexity",
        icon: "file-code",
        command: "siren.checkQualityFile",
      },
      {
        label: "Check workspace",
        tooltip: "Code quality for every Python file in the workspace; results in the Problems panel",
        icon: "checklist",
        command: "siren.checkQuality",
      },
      {
        label: "Check .env",
        tooltip: "Compare .env with .env.example and mark keys missing from either",
        icon: "symbol-key",
        command: "siren.checkEnv",
      },
      {
        label: "New from template",
        tooltip: "Create a script, class, data class, test or package",
        icon: "new-file",
        command: "siren.newFromTemplate",
      },
    ],
  },
];

type Node = Group | Action;

/** Top section of the Siren sidebar: every command one click away. */
export class ActionsView implements vscode.TreeDataProvider<Node> {
  private readonly changed = new vscode.EventEmitter<void>();
  readonly onDidChangeTreeData = this.changed.event;
  private django = false;

  /** Show the Django actions once the workspace turns out to be a Django project. */
  setDjango(isDjango: boolean): void {
    if (this.django !== isDjango) {
      this.django = isDjango;
      this.changed.fire();
    }
  }

  getChildren(node?: Node): Node[] {
    if (!node) {
      return GROUPS;
    }
    return "actions" in node ? node.actions.filter((a) => !a.onlyFor || (a.onlyFor === "django" && this.django)) : [];
  }

  getTreeItem(node: Node): vscode.TreeItem {
    if ("actions" in node) {
      const item = new vscode.TreeItem(node.label, vscode.TreeItemCollapsibleState.Expanded);
      item.iconPath = new vscode.ThemeIcon(node.icon);
      return item;
    }
    const item = new vscode.TreeItem(node.label);
    item.description = node.description;
    item.tooltip = node.tooltip;
    item.iconPath = new vscode.ThemeIcon(node.icon);
    item.command = { command: node.command, title: node.label };
    return item;
  }
}
