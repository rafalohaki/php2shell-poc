FROM wordpress:7.1.3-php8.4-apache
RUN mkdir -p /var/www/html/wp-content/plugins/vtl /tmp/sess \
 && chmod 1777 /tmp/sess
COPY plugin.php /var/www/html/wp-content/plugins/vtl/
COPY php.ini /usr/local/etc/php/conf.d/zz-lab.ini
RUN chown -R www-data:www-data /var/www/html/wp-content/plugins/vtl
