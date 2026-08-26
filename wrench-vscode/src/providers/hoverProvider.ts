import * as vscode from 'vscode';
import { CompilerBridge } from '../services/compilerBridge';
import { ALL_SYMBOLS, SymbolMeta } from '../keywords';

export class WrenchHoverProvider implements vscode.HoverProvider {

    public provideHover(
        document: vscode.TextDocument, 
        position: vscode.Position, 
        token: vscode.CancellationToken
    ): vscode.ProviderResult<vscode.Hover> {
        
        const range = document.getWordRangeAtPosition(position);
        if(!range) {
            return null;
        }

        const word = document.getText(range);

        // 1. Static Symbols
        if (ALL_SYMBOLS[word]) {
            const meta: SymbolMeta = ALL_SYMBOLS[word];
            const markdown = new vscode.MarkdownString();

            markdown.appendCodeblock(meta.detail, 'wrench');
            markdown.appendMarkdown(`\n\n${meta.description}`);

            if (meta.returnType) {
                markdown.appendMarkdown(`\n\n**Return Type:** \`${meta.returnType}\``);
            }

            return new vscode.Hover(markdown, range);
        }

        // 2. CompilerBridge
        const compilerBridge = CompilerBridge.getInstance();
        const symbols = compilerBridge.getSymbols(document.uri.toString());

        if (symbols) {

            if (symbols.functions && symbols.functions[word]) {
                const func = symbols.functions[word];
                const retType = func.return_type || 'unit';

                let argStr = '';
                if (func.args && Array.isArray(func.args)) {
                    argStr = func.args.map((a: any) => `${a[1]}: ${a[0]}`).join(', ');
                }

                const markdown = new vscode.MarkdownString();
                markdown.appendCodeblock(`define ${word}(${argStr}) -> ${retType}`, 'wrench');
                markdown.appendMarkdown(`\n\n*User-defined function*`);
                if (func.line) {
                    markdown.appendMarkdown(`\n\n**Location:** Line ${func.line}`);
                }

                return new vscode.Hover(markdown, range);
            }

            if (symbols.classes && symbols.classes[word]) {
                const cls = symbols.classes[word];
                const markdown = new vscode.MarkdownString();

                let header = `class ${word}`;
                if (cls.parent) {
                    header += `extends ${cls.parent}`;
                }

                markdown.appendCodeblock(header, 'wrench');
                markdown.appendMarkdown(`\n\n*User-defined class*`);

                if (cls.methods && Object.keys(cls.methods).length > 0) {
                    const methodList = Object.keys(cls.methods).map(m => `\`${m}()\``).join(', ');
                    markdown.appendMarkdown(`\n\n**Methods:** ${methodList}`);
                }

                if (cls.fields && Object.keys(cls.fields).length > 0) {
                    const fieldList = Object.keys(cls.fields).map(f => `\`${f}\``).join(', ');
                    markdown.appendMarkdown(`\n\n**Fields:** ${fieldList}`);
                }

                return new vscode.Hover(markdown, range);
            }

            if (symbols.globals && symbols.globals[word]) {
                const markdown = new vscode.MarkdownString();
                markdown.appendCodeblock(`global ${word}`, 'wrench');
                markdown.appendMarkdown(`\n\n*User-defined global symbol*`);

                return new vscode.Hover(markdown, range);
            }
        }

        return null;
    }
}