import * as vscode from 'vscode';
import { CompilerBridge } from './services/compilerBridge';
import { WrenchCompletionItemProvider } from './providers/completionProvider';
import { WrenchHoverProvider } from './providers/hoverProvider';
import { WrenchDefinitionProvider } from './providers/definitionProvider';
import { WrenchRunner } from './runner';

export function activate(context: vscode.ExtensionContext) {
    const compilerBridge = CompilerBridge.getInstance();

    // Language Providers
    context.subscriptions.push(
        vscode.languages.registerCompletionItemProvider('wrench', new WrenchCompletionItemProvider(), '.', ':', ' '),
        vscode.languages.registerHoverProvider('wrench', new WrenchHoverProvider()),
        vscode.languages.registerDefinitionProvider('wrench', new WrenchDefinitionProvider())
    );
    // Event Listeners
    if (vscode.window.activeTextEditor) {
        compilerBridge.requestSymbolUpdate(vscode.window.activeTextEditor.document, 0);
    }

    context.subscriptions.push(
        vscode.workspace.onDidSaveTextDocument((doc) => compilerBridge.requestSymbolUpdate(doc, 0)),
        vscode.workspace.onDidChangeTextDocument((e) => compilerBridge.requestSymbolUpdate(e.document, 400)),
        vscode.workspace.onDidCloseTextDocument((doc) => compilerBridge.clearCache(doc.uri.toString()))
    );

    // Runner Commands
    context.subscriptions.push(
        vscode.commands.registerCommand('wrench.compile', () => WrenchRunner.runCommand('')),
        vscode.commands.registerCommand('wrench.run', () => WrenchRunner.runCommand('--run')),
        vscode.commands.registerCommand('wrench.runKeep', () => WrenchRunner.runCommand('--keep')),
        vscode.commands.registerCommand('wrench.emitSymbols', () => WrenchRunner.runCommand('--symbols')),
        vscode.commands.registerCommand('wrench.runNoStrict', () => WrenchRunner.runCommand('--no-strict'))
    );
}

export function deactivate() {}