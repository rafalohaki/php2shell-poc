FROM php:8.5-cli
RUN mkdir -p /tmp/sess && chmod 1777 /tmp/sess
COPY php.ini /usr/local/etc/php/conf.d/zz-lab.ini
COPY index.php view.php home.php /app/
WORKDIR /app
EXPOSE 8088
CMD ["php", "-S", "0.0.0.0:8088", "-t", "/app"]
