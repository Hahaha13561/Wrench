import * as vscode from 'vscode';
import { CompilerBridge } from '../services/compilerBridge';

export class WrenchDefinitionProvider implements vscode.DefinitionProvider {

    public provideDefinition(
        document: vscode.TextDocument,
        position: vscode.Position,
        token: vscode.CancellationToken
    ): vscode.ProviderResult<vscode.Definition> {

        const range = document.getWordRangeAtPosition(position);
        if (!range) {
            return null;
        }

        const word = document.getText(range);
        const compilerBridge = CompilerBridge.getInstance();
        const symbols = compilerBridge.getSymbols(document.uri.toString());

        if (!symbols) {
            return null;
        }

        if (symbols.functions && symbols.functions[word]) {
            const func = symbols.functions[word];
            if (typeof func.line === 'number') {
                const line = Math.max(0, func.line - 1);
                const col = Math.max(0, (func.col || 1) - 1);
                const targetUri = func.file_path ? vscode.Uri.file(func.file_path) : document.uri;
                return new vscode.Location(targetUri, new vscode.Position(line, col));
            }
        }

        if (symbols.classes && symbols.classes[word]) {
            const cls = symbols.classes[word];
            if (typeof cls.line === 'number') {
                const line = Math.max(0, cls.line - 1);
                const col = Math.max(0, (cls.col || 1) - 1);
                const targetUri = cls.file_path ? vscode.Uri.file(cls.file_path) : document.uri;
                return new vscode.Location(targetUri, new vscode.Position(line, col));
            }
        }

        if (symbols.globals && symbols.globals[word]) {
            const glob = symbols.globals[word];
            if (typeof glob === 'object' && typeof glob.line === 'number') {
                const line = Math.max(0, glob.line - 1);
                const col = Math.max(0, (glob.col || 1) - 1);
                const targetUri = glob.file_path ? vscode.Uri.file(glob.file_path) : document.uri;
                return new vscode.Location(targetUri, new vscode.Position(line, col));
            }
        }

        return null;
    }
}