<?php
/**
 * Plugin Name: Mijn Invoicing Connector
 * Description: Example WooCommerce connector that sends completed orders to the Mijn Invoicing API.
 * Version: 0.1
 * Author: Auto-generated
 */

if ( ! defined( 'ABSPATH' ) ) {
    exit; // Exit if accessed directly
}

// Configure your API endpoint and API key here or use WP options to store them
define('MIJN_API_URL', 'https://api.example.com');
define('MIJN_API_KEY', 'REPLACE_WITH_API_KEY');

function mijn_send_invoice_on_complete($order_id) {
    $order = wc_get_order($order_id);
    if (!$order) return;

    // Build simple invoice payload from the order
    $items = [];
    foreach ($order->get_items() as $item_id => $item) {
        $product = $item->get_product();
        $items[] = [
            'product_name' => $item->get_name(),
            'quantity' => (int)$item->get_quantity(),
            'unit_price' => (float)$item->get_total() / max(1, (int)$item->get_quantity()),
            'vat_rate' => 0.00, // WooCommerce taxes could be mapped here
        ];
    }

    $customer = [
        'name' => $order->get_billing_first_name() . ' ' . $order->get_billing_last_name(),
        'email' => $order->get_billing_email(),
        'address' => [
            'line1' => $order->get_billing_address_1(),
            'city' => $order->get_billing_city(),
            'postal_code' => $order->get_billing_postcode(),
            'country' => $order->get_billing_country(),
        ],
        'vat_number' => '',
    ];

    $payload = [
        'shop_id' => 'REPLACE_SHOP_ID',
        'customer' => $customer,
        'items' => $items,
    ];

    $url = rtrim(MIJN_API_URL, '/') . '/invoices';

    $args = array(
        'body' => wp_json_encode($payload),
        'headers' => array(
            'Content-Type' => 'application/json',
            'X-API-Key' => MIJN_API_KEY,
        ),
        'timeout' => 15,
    );

    $response = wp_remote_post($url, $args);
    if (is_wp_error($response)) {
        error_log('Mijn Invoicing: API request failed: ' . $response->get_error_message());
        return;
    }

    $code = wp_remote_retrieve_response_code($response);
    $body = wp_remote_retrieve_body($response);
    if ($code < 200 || $code >= 300) {
        error_log('Mijn Invoicing: API responded ' . $code . ' - ' . $body);
    }
}
add_action('woocommerce_order_status_completed', 'mijn_send_invoice_on_complete', 10, 1);

?>
