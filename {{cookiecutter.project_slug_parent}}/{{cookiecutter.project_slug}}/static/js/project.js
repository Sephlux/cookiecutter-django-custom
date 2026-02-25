{%- if cookiecutter.frontend_pipeline == 'Webpack' -%}
import '../sass/project.scss';

{% endif -%}
/* Project specific Javascript goes here. */
/* Project specific Javascript goes here. */


function themeState() {
    return {
        storageKey: 'app.theme',
        lightTheme: 'light',
        darkTheme: 'dark',
        isDark: false,

        initTheme() {
            const saved = localStorage.getItem(this.storageKey);

            if (saved === this.lightTheme || saved === this.darkTheme) {
                this.isDark = saved === this.darkTheme;
            } else {
                // Default preference: dark
                this.isDark = true;
                localStorage.setItem(this.storageKey, this.darkTheme);
            }

            // Ensure daisyUI actually applies the theme on first load
            this.syncThemeControllers();

            this.$watch('isDark', (val) => {
                localStorage.setItem(this.storageKey, val ? this.darkTheme : this.lightTheme);
                this.syncThemeControllers();
            });

            // Cross-tab/window sync (fires in *other* tabs when localStorage changes)
            window.addEventListener('storage', (e) => {
                if (e.key !== this.storageKey) return;

                const next = e.newValue;
                if (next !== this.lightTheme && next !== this.darkTheme) return;

                const nextIsDark = next === this.darkTheme;
                if (nextIsDark === this.isDark) return;

                this.isDark = nextIsDark; // triggers $watch -> syncThemeControllers()
            });
        },

        syncThemeControllers() {
            // daisyUI's theme-controller listens to user events; Alpine model updates may not emit them.
            const controllers = document.querySelectorAll('input.theme-controller[type="checkbox"]');

            controllers.forEach((el) => {
                el.value = this.darkTheme;     // checked => "dark"
                el.checked = this.isDark;      // sync UI state
                el.dispatchEvent(new Event('change', {bubbles: true})); // notify daisyUI
            });
        },
    };
}

function drawerState() {
    return {
        drawerStorageKey: 'app.drawer.open',
        drawerOpen: false,
        drawerReady: false,
        lgMql: null,

        isLargeScreen() {
            return !!this.lgMql?.matches;
        },

        readSavedDrawerOpen() {
            const saved = localStorage.getItem(this.drawerStorageKey);
            if (saved === '1' || saved === '0') return saved === '1';
            return null;
        },

        applyDrawerForViewport() {
            if (!this.isLargeScreen()) {
                // Small screens ignored
                return;
            }

            const savedOpen = this.readSavedDrawerOpen();
            this.drawerOpen = savedOpen ?? true;

            if (savedOpen === null) {
                localStorage.setItem(this.drawerStorageKey, '1');
            }
        },

        initDrawer() {
            this.lgMql = window.matchMedia('(min-width: 1024px)');

            // Disable animation during the first paint where we apply drawerOpen
            this.drawerReady = false;

            this.applyDrawerForViewport();

            // Re-enable animation after the DOM has applied the initial checked state
            requestAnimationFrame(() => {
                this.drawerReady = true;
            });

            this.$watch('drawerOpen', (val) => {
                if (!this.isLargeScreen()) return;
                localStorage.setItem(this.drawerStorageKey, val ? '1' : '0');
            });

            this.lgMql.addEventListener('change', () => {
                this.drawerReady = false;
                this.applyDrawerForViewport();
                requestAnimationFrame(() => {
                    this.drawerReady = true;
                });
            });

            window.addEventListener('storage', (e) => {
                if (e.key !== this.drawerStorageKey) return;
                if (!this.isLargeScreen()) return;

                const next = e.newValue;
                if (next !== '0' && next !== '1') return;

                const nextOpen = next === '1';
                if (nextOpen === this.drawerOpen) return;

                this.drawerOpen = nextOpen;
            });
        },
    };
}




