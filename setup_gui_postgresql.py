"""
PostgreSQL-only DatabasePage for setup_gui.py
This will replace the existing DatabasePage class
"""

class DatabasePage(WizardPage):
    """PostgreSQL database configuration page"""

    def __init__(self, parent):
        super().__init__(parent, "PostgreSQL Database Configuration")

        # Title and description
        title_label = ttk.Label(self, text="PostgreSQL Database Setup", font=("Helvetica", 12, "bold"))
        title_label.pack(pady=10)

        desc_text = """GiljoAI MCP requires PostgreSQL for reliable multi-user operation.
Choose how you want to set up PostgreSQL:"""
        desc_label = ttk.Label(self, text=desc_text, justify=tk.LEFT)
        desc_label.pack(padx=20, pady=5)

        # PostgreSQL setup mode selection
        self.setup_mode_var = tk.StringVar(value="existing")

        mode_frame = ttk.LabelFrame(self, text="PostgreSQL Setup Mode", padding=10)
        mode_frame.pack(padx=20, pady=10, fill="x")

        ttk.Radiobutton(
            mode_frame,
            text="Attach to Existing PostgreSQL Server",
            variable=self.setup_mode_var,
            value="existing",
            command=self._on_mode_change,
        ).pack(anchor="w")

        existing_desc = ttk.Label(
            mode_frame,
            text="   • Use an already installed PostgreSQL server\n   • You'll provide connection credentials",
            foreground="gray"
        )
        existing_desc.pack(anchor="w", padx=20, pady=(0, 10))

        ttk.Radiobutton(
            mode_frame,
            text="Install Fresh PostgreSQL Server",
            variable=self.setup_mode_var,
            value="fresh",
            command=self._on_mode_change,
        ).pack(anchor="w")

        fresh_desc = ttk.Label(
            mode_frame,
            text="   • We'll download and install PostgreSQL\n   • Automatically configure for GiljoAI",
            foreground="gray"
        )
        fresh_desc.pack(anchor="w", padx=20)

        # Connection configuration frame (for both modes)
        self.config_frame = ttk.LabelFrame(self, text="Database Connection Details", padding=10)
        self.config_frame.pack(padx=20, pady=10, fill="x")

        # Network configuration
        network_frame = ttk.Frame(self.config_frame)
        network_frame.pack(fill="x", pady=5)

        ttk.Label(network_frame, text="Network Mode:", width=15).pack(side="left")
        self.network_mode_var = tk.StringVar(value="localhost")
        self.network_combo = ttk.Combobox(
            network_frame,
            textvariable=self.network_mode_var,
            values=["localhost", "network"],
            state="readonly",
            width=27
        )
        self.network_combo.pack(side="left", padx=5)
        self.network_combo.bind("<<ComboboxSelected>>", self._on_network_change)

        # Host/IP (shown for network mode or existing server)
        self.host_frame = ttk.Frame(self.config_frame)
        self.pg_host_var = tk.StringVar(value="localhost")
        ttk.Label(self.host_frame, text="Host/IP:", width=15).pack(side="left")
        self.host_entry = ttk.Entry(self.host_frame, textvariable=self.pg_host_var, width=30)
        self.host_entry.pack(side="left", padx=5)

        # Port
        port_frame = ttk.Frame(self.config_frame)
        port_frame.pack(fill="x", pady=2)
        self.pg_port_var = tk.StringVar(value="5432")
        ttk.Label(port_frame, text="Port:", width=15).pack(side="left")
        self.port_entry = ttk.Entry(port_frame, textvariable=self.pg_port_var, width=30)
        self.port_entry.pack(side="left", padx=5)

        # Check port button (for existing mode)
        self.check_port_btn = ttk.Button(port_frame, text="Check", command=self._check_port, width=10)

        # Database name
        db_frame = ttk.Frame(self.config_frame)
        db_frame.pack(fill="x", pady=2)
        self.pg_database_var = tk.StringVar(value="giljo_mcp")
        ttk.Label(db_frame, text="Database Name:", width=15).pack(side="left")
        ttk.Entry(db_frame, textvariable=self.pg_database_var, width=30).pack(side="left", padx=5)

        db_help = ttk.Label(db_frame, text="(Will be created if doesn't exist)", foreground="gray")
        db_help.pack(side="left", padx=5)

        # Credentials section
        cred_separator = ttk.Separator(self.config_frame, orient="horizontal")
        cred_separator.pack(fill="x", pady=10)

        cred_label = ttk.Label(self.config_frame, text="Database Credentials", font=("Helvetica", 10, "bold"))
        cred_label.pack(anchor="w")

        # Username
        user_frame = ttk.Frame(self.config_frame)
        user_frame.pack(fill="x", pady=2)
        self.pg_user_var = tk.StringVar(value="postgres")
        ttk.Label(user_frame, text="Username:", width=15).pack(side="left")
        self.user_entry = ttk.Entry(user_frame, textvariable=self.pg_user_var, width=30)
        self.user_entry.pack(side="left", padx=5)

        # Password
        pass_frame = ttk.Frame(self.config_frame)
        pass_frame.pack(fill="x", pady=2)
        self.pg_password_var = tk.StringVar()
        ttk.Label(pass_frame, text="Password:", width=15).pack(side="left")
        self.pass_entry = ttk.Entry(pass_frame, textvariable=self.pg_password_var, show="*", width=30)
        self.pass_entry.pack(side="left", padx=5)

        # Show/hide password
        self.show_pass_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            pass_frame,
            text="Show",
            variable=self.show_pass_var,
            command=self._toggle_password
        ).pack(side="left", padx=5)

        # Important note for fresh install
        self.note_frame = ttk.Frame(self.config_frame)
        note_label = ttk.Label(
            self.note_frame,
            text="⚠️ IMPORTANT: Write down these credentials! You'll need them to access the database.",
            foreground="red",
            font=("Helvetica", 9, "bold")
        )
        note_label.pack(pady=5)

        # Test connection button (for existing mode)
        self.test_frame = ttk.Frame(self.config_frame)
        self.test_btn = ttk.Button(
            self.test_frame,
            text="Test Connection",
            command=self._test_connection,
            style="Accent.TButton"
        )
        self.test_btn.pack(pady=10)

        self.status_label = ttk.Label(self.test_frame, text="")
        self.status_label.pack()

        # Install note (for fresh mode)
        self.install_note_frame = ttk.Frame(self.config_frame)
        install_note = ttk.Label(
            self.install_note_frame,
            text="PostgreSQL will be downloaded and installed during the installation process.",
            foreground="blue"
        )
        install_note.pack(pady=5)

        # Initialize visibility based on mode
        self._on_mode_change()

    def _on_mode_change(self):
        """Handle setup mode change"""
        mode = self.setup_mode_var.get()

        if mode == "existing":
            # Show test connection, host entry, check port
            self.test_frame.pack(fill="x", pady=5)
            self.install_note_frame.pack_forget()
            self.note_frame.pack_forget()
            self.host_frame.pack(fill="x", pady=2, after=self.network_combo.master)
            self.check_port_btn.pack(side="left", padx=5)
            self.host_entry.config(state="normal")
            # Enable network mode selection
            self.network_combo.config(state="readonly")
        else:  # fresh
            # Hide test connection, show install note
            self.test_frame.pack_forget()
            self.install_note_frame.pack(fill="x", pady=5)
            self.note_frame.pack(fill="x", pady=5, after=self.pass_entry.master)
            self.check_port_btn.pack_forget()
            # For fresh install, configure based on network mode
            self._on_network_change()

    def _on_network_change(self, event=None):
        """Handle network mode change"""
        network_mode = self.network_mode_var.get()
        setup_mode = self.setup_mode_var.get()

        if setup_mode == "fresh":
            if network_mode == "localhost":
                # Hide host entry for localhost fresh install
                self.host_frame.pack_forget()
                self.pg_host_var.set("localhost")
            else:
                # Show host entry for network fresh install
                self.host_frame.pack(fill="x", pady=2, after=self.network_combo.master)
                # Get local IP suggestion
                import socket
                try:
                    hostname = socket.gethostname()
                    local_ip = socket.gethostbyname(hostname)
                    self.pg_host_var.set(local_ip)
                except:
                    self.pg_host_var.set("0.0.0.0")  # Listen on all interfaces

    def _toggle_password(self):
        """Toggle password visibility"""
        if self.show_pass_var.get():
            self.pass_entry.config(show="")
        else:
            self.pass_entry.config(show="*")

    def _check_port(self):
        """Check if PostgreSQL port is accessible"""
        try:
            import socket
            host = self.pg_host_var.get()
            port = int(self.pg_port_var.get())

            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex((host, port))
            sock.close()

            if result == 0:
                self.status_label.config(text=f"✓ Port {port} is open on {host}", foreground="green")
            else:
                self.status_label.config(text=f"✗ Port {port} is not accessible on {host}", foreground="red")
        except Exception as e:
            self.status_label.config(text=f"✗ Error checking port: {e}", foreground="red")

    def _test_connection(self):
        """Test PostgreSQL connection"""
        self.status_label.config(text="Testing connection...", foreground="blue")
        self.update()

        # Run test in thread to avoid blocking
        def test():
            try:
                import psycopg2

                # First try to connect to the postgres database to check credentials
                conn = psycopg2.connect(
                    host=self.pg_host_var.get(),
                    port=self.pg_port_var.get(),
                    database="postgres",  # Connect to default database first
                    user=self.pg_user_var.get(),
                    password=self.pg_password_var.get(),
                    connect_timeout=5
                )

                # Check if our database exists
                cur = conn.cursor()
                db_name = self.pg_database_var.get()
                cur.execute(
                    "SELECT 1 FROM pg_database WHERE datname = %s",
                    (db_name,)
                )
                db_exists = cur.fetchone() is not None

                cur.close()
                conn.close()

                if db_exists:
                    # Try connecting to the actual database
                    conn2 = psycopg2.connect(
                        host=self.pg_host_var.get(),
                        port=self.pg_port_var.get(),
                        database=db_name,
                        user=self.pg_user_var.get(),
                        password=self.pg_password_var.get(),
                        connect_timeout=5
                    )
                    conn2.close()
                    self.status_label.config(
                        text=f"✓ Connected successfully! Database '{db_name}' exists.",
                        foreground="green"
                    )
                else:
                    self.status_label.config(
                        text=f"✓ Connection successful! Database '{db_name}' will be created.",
                        foreground="green"
                    )

            except psycopg2.OperationalError as e:
                if "password authentication failed" in str(e):
                    self.status_label.config(text="✗ Invalid credentials", foreground="red")
                elif "could not connect to server" in str(e):
                    self.status_label.config(text="✗ Cannot connect to server", foreground="red")
                elif "timeout expired" in str(e):
                    self.status_label.config(text="✗ Connection timeout", foreground="red")
                else:
                    self.status_label.config(text=f"✗ Connection failed: {e}", foreground="red")
            except Exception as e:
                self.status_label.config(text=f"✗ Error: {e}", foreground="red")

        thread = threading.Thread(target=test)
        thread.daemon = True
        thread.start()

    def validate(self) -> bool:
        """Validate database configuration"""
        # All fields are required
        if not all([
            self.pg_host_var.get(),
            self.pg_port_var.get(),
            self.pg_database_var.get(),
            self.pg_user_var.get(),
            self.pg_password_var.get()
        ]):
            messagebox.showerror("Validation Error", "All database fields are required.")
            return False

        # Validate port is a number
        try:
            port = int(self.pg_port_var.get())
            if port < 1 or port > 65535:
                messagebox.showerror("Validation Error", "Port must be between 1 and 65535.")
                return False
        except ValueError:
            messagebox.showerror("Validation Error", "Port must be a valid number.")
            return False

        # For existing mode, recommend testing connection
        if self.setup_mode_var.get() == "existing":
            if not hasattr(self, '_connection_tested'):
                result = messagebox.askyesno(
                    "Connection Test",
                    "Would you like to test the database connection before proceeding?"
                )
                if result:
                    self._test_connection()
                    return False  # Don't proceed yet, let user see result

        return True

    def get_data(self) -> dict:
        """Return database configuration"""
        return {
            "db_type": "postgresql",  # Always PostgreSQL now
            "pg_setup_mode": self.setup_mode_var.get(),
            "pg_network_mode": self.network_mode_var.get(),
            "pg_host": self.pg_host_var.get(),
            "pg_port": self.pg_port_var.get(),
            "pg_database": self.pg_database_var.get(),
            "pg_user": self.pg_user_var.get(),
            "pg_password": self.pg_password_var.get(),
            "install_postgresql": self.setup_mode_var.get() == "fresh"
        }

    def on_enter(self):
        """Called when entering the page"""
        # Reset connection tested flag
        if hasattr(self, '_connection_tested'):
            delattr(self, '_connection_tested')

        # Get deployment mode from parent
        parent = self.parent
        while parent and not hasattr(parent, "config_data"):
            parent = parent.master

        if parent and hasattr(parent, "config_data"):
            deployment_mode = parent.config_data.get("deployment_mode", "local")

            # Set network mode based on deployment
            if deployment_mode == "local":
                self.network_mode_var.set("localhost")
            else:
                self.network_mode_var.set("network")

            self._on_network_change()
