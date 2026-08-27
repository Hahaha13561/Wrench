import * as vscode from 'vscode';
import { CompilerBridge, WrenchSymbolTable } from '../services/compilerBridge';
import { 
    BUILTIN_FUNCTIONS, 
    CONTROL_KEYWORDS, 
    DECLARATION_KEYWORDS, 
    OPERATOR_KEYWORDS, 
    VALUE_KEYWORDS, 
    DATA_TYPES,
    ASSIGNMENT_OPERATORS,
    COMPARISON_OPERATORS,
    ARITHMETIC_OPERATORS,
    SymbolMeta 
} from '../keywords';

export class WrenchCompletionItemProvider implements vscode.CompletionItemProvider {

    public provideCompletionItems(
        document: vscode.TextDocument,
        position: vscode.Position,
        token: vscode.CancellationToken,
        context: vscode.CompletionContext
    ): vscode.ProviderResult<vscode.CompletionItem[] | vscode.CompletionList> {

        const items: vscode.CompletionItem[] = [];
        const lineText = document.lineAt(position).text;
        const linePrefix = lineText.substring(0, position.character);

        // 1. Member Access filling after '.'
        if (linePrefix.endsWith('.')) {
            return this.provideMemberCompletions(document, linePrefix);
        }

        // 2. Static Syntax Symbols (keywords.ts)
        this.addStaticKeywords(items, CONTROL_KEYWORDS, vscode.CompletionItemKind.Keyword);
        this.addStaticKeywords(items, DECLARATION_KEYWORDS, vscode.CompletionItemKind.Keyword);
        this.addStaticKeywords(items, OPERATOR_KEYWORDS, vscode.CompletionItemKind.Operator);
        this.addStaticKeywords(items, VALUE_KEYWORDS, vscode.CompletionItemKind.Value);
        this.addStaticKeywords(items, DATA_TYPES, vscode.CompletionItemKind.Class);
        this.addStaticKeywords(items, BUILTIN_FUNCTIONS, vscode.CompletionItemKind.Function);
        this.addStaticKeywords(items, ASSIGNMENT_OPERATORS, vscode.CompletionItemKind.Operator);
        this.addStaticKeywords(items, COMPARISON_OPERATORS, vscode.CompletionItemKind.Operator);
        this.addStaticKeywords(items, ARITHMETIC_OPERATORS, vscode.CompletionItemKind.Operator);

        // 3. CompilerBridge
        const compilerBridge = CompilerBridge.getInstance();
        const symbolTable = compilerBridge.getSymbols(document.uri.toString());

        if (symbolTable) {
            this.addDynamicSymbols(items, symbolTable);
        }

        return items;
    }

    private addStaticKeywords(
        items: vscode.CompletionItem[],
        dict: Record<string, SymbolMeta>,
        kind: vscode.CompletionItemKind
    ): void {
        for (const [key, meta] of Object.entries(dict)) {
            const item = new vscode.CompletionItem(key, kind);
            item.detail = meta.detail;
            item.documentation = new vscode.MarkdownString(meta.description);

            if (meta.snippet) {
                item.insertText = new vscode.SnippetString(meta.snippet);
            } else if (kind === vscode.CompletionItemKind.Function) {
                item.insertText = new vscode.SnippetString(`${key}($0)`);
            }

            items.push(item);
        }
    }

    private addDynamicSymbols(items: vscode.CompletionItem[], symbols: WrenchSymbolTable): void {
        if (symbols.functions) {
            for (const [funcName, funcInfo] of Object.entries(symbols.functions)) {
                const item = new vscode.CompletionItem(funcName, vscode.CompletionItemKind.Function);
                const retType = funcInfo.return_type || 'unit';
                
                let argStr = '';
                if (funcInfo.args && Array.isArray(funcInfo.args)) {
                    argStr = funcInfo.args.map((a: any) => `${a[1]}: ${a[0]}`).join(', ');
                }

                item.detail = `define ${funcName}(${argStr}) -> ${retType}`;
                item.insertText = new vscode.SnippetString(`${funcName}($0)`);
                item.documentation = new vscode.MarkdownString(`*User Function*\n\nReturn Type: \`${retType}\``);
                items.push(item);
            }
        }

        if (symbols.classes) {
            for (const [className, classInfo] of Object.entries(symbols.classes)) {
                const item = new vscode.CompletionItem(className, vscode.CompletionItemKind.Class);
                item.detail = `class ${className}`;
                if (classInfo.parent) {
                    item.detail += ` extends ${classInfo.parent}`;
                }
                item.documentation = new vscode.MarkdownString(`*Class Definition*`);
                items.push(item);
            }
        }

        if (symbols.globals) {
            for (const [varName, varInfo] of Object.entries(symbols.globals)) {
                const item = new vscode.CompletionItem(varName, vscode.CompletionItemKind.Variable);
                item.detail = `global ${varName}`;
                item.documentation = new vscode.MarkdownString(`*Global Variable*`);
                items.push(item);
            }
        }
    }

    private provideMemberCompletions(document: vscode.TextDocument, linePrefix: string): vscode.CompletionItem[] {
        const items: vscode.CompletionItem[] = [];
        const match = linePrefix.match(/([A-Za-z_]\w*)\.$/);
        
        if (!match) {
            return items;
        }

        const varName = match[1];
        const compilerBridge = CompilerBridge.getInstance();
        const symbols = compilerBridge.getSymbols(document.uri.toString());

        if (!symbols || !symbols.classes) {
            return items;
        }

        const targetClassName = this.resolveVariableType(document, varName, symbols);
        
        if (targetClassName && symbols.classes[targetClassName]) {
            const classInfo = symbols.classes[targetClassName];
            if (classInfo.methods) {
                for (const [methodName, mInfo] of Object.entries<any>(classInfo.methods)) {
                    const item = new vscode.CompletionItem(methodName, vscode.CompletionItemKind.Method);
                    const retType = mInfo.return_type || 'unit';
                    item.detail = `(method) ${targetClassName}.${methodName} -> ${retType}`;
                    item.insertText = new vscode.SnippetString(`${methodName}($0)`);
                    items.push(item);
                }
            }
            if (classInfo.fields) {
                for (const [fieldName, fInfo] of Object.entries<any>(classInfo.fields)) {
                    const item = new vscode.CompletionItem(fieldName, vscode.CompletionItemKind.Field);
                    item.detail = `(property) ${targetClassName}.${fieldName}`;
                    items.push(item);
                }
            }
        }
        return items;
    }

    private resolveVariableType(document: vscode.TextDocument, varName: string, symbols: WrenchSymbolTable): string | null {
        if (symbols.classes[varName]) {
            return varName;
        }

        const fullText = document.getText();

        if (varName === 'this') {
            const classMatch = fullText.match(/class\s+([A-Za-z_]\w*)/);
            return classMatch ? classMatch[1] : null;
        }

        const newPattern = new RegExp(`\\b${varName}\\s*=\\s*new\\s+([A-Za-z_]\\w*)`);
        const newMatch = fullText.match(newPattern);
        if (newMatch && symbols.classes[newMatch[1]]) {
            return newMatch[1];
        }

        const typePattern = new RegExp(`\\b${varName}\\s*:\\s*([A-Za-z_]\\w*)`);
        const typeMatch = fullText.match(typePattern);
        if (typeMatch && symbols.classes[typeMatch[1]]) {
            return typeMatch[1];
        }

        return null;
    }
}
