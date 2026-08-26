import * as vscode from 'vscode';
import * as path from 'path';
import { clear } from 'console';

export class WrenchRunner {
    private static terminal: vscode.Terminal | undefined;

    public static runCommand(flags: string = ''): void {
        const editor = vscode.window.activeTextEditor;
        if (!editor || editor.document.languageId !== 'wrench') {
            vscode.window.showWarningMessage('A `.wr` file is not open.');
            return;
        }

        if (editor.document.isDirty) {
            editor.document.save();
        }

        const filePath = editor.document.fileName;
        const config = vscode.workspace.getConfiguration('wrench');
        const pythonPath = config.get<string>('pythonPath') || 'python3';
        const defaultFlags = config.get<string>('defaultFlags') || '';
        const clearTerminal = config.get<boolean>('clearTerminalBeforeRun') ?? true;
        
        let compilerPath = config.get<string>('compilerPath');
        if (!compilerPath) {
            const workspaceFolders = vscode.workspace.workspaceFolders;
            if (workspaceFolders && workspaceFolders.length > 0) {
                compilerPath = path.join(workspaceFolders[0].uri.fsPath, 'wrench.py');
            } else {
                compilerPath = path.join(path.dirname(filePath), 'wrench.py');
            }
        }

        const combinedFlags = `${defaultFlags} ${flags}`.trim();
        const fullCommand = `"${pythonPath}" "${compilerPath}" "${filePath}" ${combinedFlags}`.trim();

        if (!this.terminal || this.terminal.exitStatus !== undefined) {
            this.terminal = vscode.window.createTerminal('Wrench');
        }

        if (clearTerminal) {
            const clearCmd = process.platform === 'win32' ? 'cls' : 'clear';
            this.terminal.sendText(clearCmd);
        }

        this.terminal.show(true);
        this.terminal.sendText(fullCommand);
    }
}