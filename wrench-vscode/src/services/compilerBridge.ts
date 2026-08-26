import * as vscode from 'vscode';
import * as cp from 'child_process';
import * as path from 'path';

export interface WrenchFunctionSymbol {
    return_type?: string;
    args?: Array<[tuple_type: any, tuple_name: any]>;
    line?: number;
    col?: number;
    [key: string]: any;
}

export interface WrenchClassSymbol {
    methods?: Record<string, WrenchFunctionSymbol>;
    fields?: Record<string, any>;
    parent?: string;
    has_init?: boolean;
    size?: number;
    line?: number;
    col?: number;
    [key: string]: any;
}

export interface WrenchSymbolTable {
    functions: Record<string, WrenchFunctionSymbol>;
    classes: Record<string, WrenchClassSymbol>;
    globals: Record<string, any>;
    error?: string;
}

export class CompilerBridge {
    private static instance: CompilerBridge;
    private symbolCache: Map<string, WrenchSymbolTable> = new Map();
    private debounceTimers: Map<string, NodeJS.Timeout> = new Map();

    private constructor() {}

    public static getInstance(): CompilerBridge {
        if (!CompilerBridge.instance) {
            CompilerBridge.instance = new CompilerBridge();
        }
        return CompilerBridge.instance;
    }

    public getSymbols(uri: string): WrenchSymbolTable | undefined {
        return this.symbolCache.get(uri);
    }

    public requestSymbolUpdate(document: vscode.TextDocument, delayMs: number = 400): void {
        if (document.languageId !== 'wrench' || document.isUntitled) {
            return;
        }

        const uriStr = document.uri.toString();
        const existingTimer = this.debounceTimers.get(uriStr);
        if (existingTimer) {
            clearTimeout(existingTimer);
        }

        const timer = setTimeout(() => {
            this.updateSymbols(document);
            this.debounceTimers.delete(uriStr);
        }, delayMs);

        this.debounceTimers.set(uriStr, timer);
    }

    public async updateSymbols(document: vscode.TextDocument): Promise<WrenchSymbolTable | null> {
        if (document.languageId !== 'wrench' || document.isUntitled) {
            return null;
        }

        const filePath = document.fileName;
        const config = vscode.workspace.getConfiguration('wrench');
        const pythonPath = config.get<string>('pythonPath') || 'python3';
        const compilerPath = config.get<string>('compilerPath') || this.resolveCompilerPath(filePath);

        if (!compilerPath) {
            return null;
        }

        return new Promise((resolve) => {
            const command = `"${pythonPath}" "${compilerPath}" "${filePath}" --symbols`;
            const cwd = path.dirname(filePath);

            cp.exec(command, { cwd }, (error: cp.ExecException | null, stdout: string, stderr: string) => {
                if (stdout) {
                    try {   
                        const parsedData: WrenchSymbolTable = JSON.parse(stdout);
                        if (!parsedData.error) {
                            this.symbolCache.set(document.uri.toString(), parsedData);
                            resolve(parsedData);
                            return;
                        }
                    } catch (e) {
                        // Standart dışı veya bozuk JSON çıktısı
                    }
                }
                resolve(null);
            });
        });
    }

    private resolveCompilerPath(currentFilePath: string): string {
        const workspaceFolders = vscode.workspace.workspaceFolders;
        if (workspaceFolders && workspaceFolders.length > 0) {
            return path.join(workspaceFolders[0].uri.fsPath, 'wrench.py');
        }
        return path.join(path.dirname(currentFilePath), 'wrench.py');
    }

    public clearCache(uri: string): void {
        const uriStr = uri.toString();
        this.symbolCache.delete(uriStr);
        const timer = this.debounceTimers.get(uriStr);
        if (timer) {
            clearTimeout(timer);
            this.debounceTimers.delete(uriStr);
        }
    }
}