#!/usr/bin/env node
/**
 * Colored frontend launcher with verbose output
 *
 * Wraps the Vite dev server with colored console output and enhanced verbosity
 */

import { spawn } from 'child_process';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

// ANSI color codes
const colors = {
  reset: '\x1b[0m',
  bright: '\x1b[1m',
  red: '\x1b[31m',
  yellow: '\x1b[33m',
  green: '\x1b[32m',
  blue: '\x1b[34m',
  cyan: '\x1b[36m',
  white: '\x1b[37m',
};

function colorize(text, color) {
  return `${colors[color]}${text}${colors.reset}`;
}

function printError(message) {
  console.log(colorize(message, 'red'));
}

function printWarning(message) {
  console.log(colorize(message, 'yellow'));
}

function printSuccess(message) {
  console.log(colorize(message, 'green'));
}

function printInfo(message) {
  console.log(colorize(message, 'blue'));
}

function printHighlight(message) {
  console.log(colorize(message, 'cyan') + colorize(message, 'bright'));
}

// Get the directory of this script
const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// Print startup banner
console.log('');
printHighlight('='.repeat(60));
printHighlight('  GiljoAI MCP - Frontend Dashboard');
printHighlight('='.repeat(60));
console.log('');

printInfo('Starting Vite development server...');
printInfo('Colored output: ENABLED');
printInfo('Verbose mode: ENABLED');
console.log('');

// Start Vite dev server
const vite = spawn('npm', ['run', 'dev'], {
  cwd: __dirname,
  shell: true,
  stdio: 'pipe',
  env: {
    ...process.env,
    FORCE_COLOR: '1', // Force color output
    NODE_ENV: 'development',
  }
});

// Process stdout with colors
vite.stdout.on('data', (data) => {
  const output = data.toString();
  const lines = output.split('\n');

  lines.forEach(line => {
    if (!line.trim()) return;

    // Color code based on content
    if (line.includes('error') || line.includes('Error') || line.includes('ERROR')) {
      printError(line);
    } else if (line.includes('warn') || line.includes('Warning') || line.includes('WARN')) {
      printWarning(line);
    } else if (
      line.includes('ready') ||
      line.includes('success') ||
      line.includes('compiled') ||
      line.includes('✓') ||
      line.includes('Local:') ||
      line.includes('Network:')
    ) {
      printSuccess(line);
    } else if (
      line.includes('vite') ||
      line.includes('VITE') ||
      line.includes('update') ||
      line.includes('hmr') ||
      line.includes('page reload')
    ) {
      printInfo(line);
    } else {
      // Default: white text for general output
      console.log(line);
    }
  });
});

// Process stderr with colors (errors in red)
vite.stderr.on('data', (data) => {
  const output = data.toString();
  const lines = output.split('\n');

  lines.forEach(line => {
    if (!line.trim()) return;

    // Warnings in yellow, errors in red
    if (line.includes('warn') || line.includes('Warning') || line.includes('WARN')) {
      printWarning(line);
    } else if (line.includes('error') || line.includes('Error') || line.includes('ERROR')) {
      printError(line);
    } else {
      printError(line); // Default stderr to red
    }
  });
});

// Handle process exit
vite.on('close', (code) => {
  console.log('');
  if (code === 0) {
    printSuccess('Vite dev server stopped successfully');
  } else {
    printError(`Vite dev server exited with code ${code}`);
  }
  process.exit(code);
});

vite.on('error', (err) => {
  printError('Failed to start Vite dev server:');
  printError(err.message);
  process.exit(1);
});

// Handle Ctrl+C gracefully
process.on('SIGINT', () => {
  console.log('');
  printInfo('Received interrupt signal, shutting down frontend...');
  vite.kill('SIGINT');
});

process.on('SIGTERM', () => {
  console.log('');
  printInfo('Received termination signal, shutting down frontend...');
  vite.kill('SIGTERM');
});
