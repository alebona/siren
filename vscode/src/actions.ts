import * as vscode from "vscode";

interface Action {
  label: string;
  description?: string;
  icon: string;
  command: string;
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
      { label: "Insert siren()", description: "Ctrl+Alt+S", icon: "add", command: "siren.insert" },
      { label: "Run current file", description: "values show inline", icon: "play", command: "siren.runFile" },
      { label: "Show captured values", icon: "output", command: "siren.showOutput" },
      { label: "Clear inline values", icon: "clear-all", command: "siren.clearInlineValues" },
    ],
  },
  {
    label: "Clean up",
    icon: "trash",
    actions: [
      { label: "Remove siren() from this file", icon: "file", command: "siren.cleanFile" },
      { label: "Remove siren() from workspace", description: "with preview", icon: "files", command: "siren.cleanWorkspace" },
    ],
  },
  {
    label: "Code",
    icon: "code",
    actions: [
      { label: "Check code quality", description: "Problems panel", icon: "checklist", command: "siren.checkQuality" },
      { label: "Check .env", description: "vs .env.example", icon: "symbol-key", command: "siren.checkEnv" },
      { label: "New from template...", icon: "new-file", command: "siren.newFromTemplate" },
    ],
  },
];

type Node = Group | Action;

/** Top section of the Siren sidebar: every command one click away. */
export class ActionsView implements vscode.TreeDataProvider<Node> {
  getChildren(node?: Node): Node[] {
    if (!node) {
      return GROUPS;
    }
    return "actions" in node ? node.actions : [];
  }

  getTreeItem(node: Node): vscode.TreeItem {
    if ("actions" in node) {
      const item = new vscode.TreeItem(node.label, vscode.TreeItemCollapsibleState.Expanded);
      item.iconPath = new vscode.ThemeIcon(node.icon);
      return item;
    }
    const item = new vscode.TreeItem(node.label);
    item.description = node.description;
    item.iconPath = new vscode.ThemeIcon(node.icon);
    item.command = { command: node.command, title: node.label };
    return item;
  }
}
