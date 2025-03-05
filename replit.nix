{pkgs}: {
  deps = [
    pkgs.glibcLocales
    pkgs.libxcrypt
    pkgs.cacert
    pkgs.postgresql_16  # Ensure PostgreSQL client libraries are available
  ];
} 