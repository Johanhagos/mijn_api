<?php
/**
 * Plugin Name: APIBlockchain - Pay with APIUSD
 * Description: WooCommerce payment method: customers pay their order in APIUSD through APIBlockchain's hosted checkout. The order is marked paid only after APIBlockchain has verified the payment on-chain.
 * Version: 1.0.0
 * Author: APIBlockchain
 * Requires Plugins: woocommerce
 */

if (!defined('ABSPATH')) {
    exit;
}

define('APIBLOCKCHAIN_APIUSD_FILE', __FILE__);
define('APIBLOCKCHAIN_APIUSD_DEFAULT_API', 'https://apiblockchain-production-production.up.railway.app');
define('APIBLOCKCHAIN_APIUSD_META', '_apiblockchain_session_id');
define('APIBLOCKCHAIN_APIUSD_CRON', 'apiblockchain_apiusd_check_orders');

add_action('plugins_loaded', 'apiblockchain_apiusd_init', 11);

// Works with WooCommerce's block checkout and order storage (HPOS)
add_action('before_woocommerce_init', function () {
    if (class_exists('\Automattic\WooCommerce\Utilities\FeaturesUtil')) {
        \Automattic\WooCommerce\Utilities\FeaturesUtil::declare_compatibility('cart_checkout_blocks', __FILE__, true);
        \Automattic\WooCommerce\Utilities\FeaturesUtil::declare_compatibility('custom_order_tables', __FILE__, true);
    }
});

// The block checkout only lists payment methods registered through its JavaScript API
add_action('woocommerce_blocks_payment_method_type_registration', function ($registry) {
    if (!class_exists('\Automattic\WooCommerce\Blocks\Payments\Integrations\AbstractPaymentMethodType')) {
        return;
    }
    require_once __DIR__ . '/includes/class-blocks-integration.php';
    $registry->register(new APIBlockchain_APIUSD_Blocks_Integration());
});

function apiblockchain_apiusd_init() {
    if (!class_exists('WC_Payment_Gateway')) {
        return;
    }

    class WC_Gateway_APIBlockchain_APIUSD extends WC_Payment_Gateway {

        public function __construct() {
            $this->id                 = 'apiblockchain_apiusd';
            $this->method_title       = 'APIBlockchain (APIUSD)';
            $this->method_description = 'Customers pay in APIUSD on APIBlockchain\'s hosted checkout. You need an APIBlockchain account with an active plan and an API key (Dashboard > API Keys).';
            $this->has_fields         = false;
            $this->supports           = array('products');

            $this->init_form_fields();
            $this->init_settings();

            $this->title       = $this->get_option('title');
            $this->description = $this->get_option('description');
            $this->enabled     = $this->get_option('enabled');

            add_action('woocommerce_update_options_payment_gateways_' . $this->id, array($this, 'process_admin_options'));
        }

        public function init_form_fields() {
            $this->form_fields = array(
                'enabled'     => array(
                    'title'   => 'Enable',
                    'type'    => 'checkbox',
                    'label'   => 'Enable Pay with APIUSD',
                    'default' => 'no',
                ),
                'title'       => array(
                    'title'   => 'Title',
                    'type'    => 'text',
                    'default' => 'Pay with APIUSD',
                ),
                'description' => array(
                    'title'   => 'Description',
                    'type'    => 'textarea',
                    'default' => 'Pay with the APIUSD stablecoin from your crypto wallet.',
                ),
                'api_key'     => array(
                    'title'       => 'API key',
                    'type'        => 'password',
                    'description' => 'Your live API key (sk_live_...) from the APIBlockchain dashboard.',
                    'default'     => '',
                ),
                'api_url'     => array(
                    'title'       => 'API URL',
                    'type'        => 'text',
                    'description' => 'Leave as is unless APIBlockchain tells you otherwise.',
                    'default'     => APIBLOCKCHAIN_APIUSD_DEFAULT_API,
                ),
            );
        }

        public function is_available() {
            // APIUSD is charged 1:1 against the order total in EUR
            if (get_woocommerce_currency() !== 'EUR' || !$this->get_option('api_key')) {
                return false;
            }
            return parent::is_available();
        }

        public function process_payment($order_id) {
            $order = wc_get_order($order_id);
            $items = array();
            foreach ($order->get_items() as $item) {
                $qty     = max(1, (int) $item->get_quantity());
                $items[] = array(
                    'name'       => $item->get_name(),
                    'quantity'   => $qty,
                    'unit_price' => round(((float) $item->get_total() + (float) $item->get_total_tax()) / $qty, 2),
                );
            }
            $extra = (float) $order->get_shipping_total() + (float) $order->get_shipping_tax();
            if ($extra > 0) {
                $items[] = array('name' => 'Shipping', 'quantity' => 1, 'unit_price' => round($extra, 2));
            }

            $address = trim(implode(', ', array_filter(array(
                $order->get_billing_address_1(),
                $order->get_billing_postcode() . ' ' . $order->get_billing_city(),
            ))));

            $response = apiblockchain_apiusd_request($this, 'POST', '/create_session', array(
                'amount'         => round((float) $order->get_total(), 2),
                'order_id'       => (string) $order->get_order_number(),
                'description'    => 'Order ' . $order->get_order_number() . ' - ' . get_bloginfo('name'),
                'customer_name'  => trim($order->get_billing_first_name() . ' ' . $order->get_billing_last_name()),
                'customer_email' => $order->get_billing_email(),
                'buyer_country'  => $order->get_billing_country(),
                'buyer_address'  => $address,
                'items'          => $items,
                'success_url'    => $this->get_return_url($order),
                'cancel_url'     => $order->get_cancel_order_url_raw(),
            ));

            if (is_wp_error($response) || empty($response['id']) || empty($response['url'])) {
                $message = is_wp_error($response) ? $response->get_error_message() : 'unexpected response';
                $order->add_order_note('APIUSD checkout could not be started: ' . $message);
                wc_add_notice('Paying with APIUSD is not possible right now. Please choose another payment method or try again later.', 'error');
                return array('result' => 'failure');
            }

            $order->update_meta_data(APIBLOCKCHAIN_APIUSD_META, sanitize_text_field($response['id']));
            $order->update_status('pending', 'Waiting for the APIUSD payment.');
            $order->save();

            return array('result' => 'success', 'redirect' => esc_url_raw($response['url']));
        }
    }

    add_filter('woocommerce_payment_gateways', function ($gateways) {
        $gateways[] = 'WC_Gateway_APIBlockchain_APIUSD';
        return $gateways;
    });
}

function apiblockchain_apiusd_gateway() {
    if (!function_exists('WC')) {
        return null;
    }
    $gateways = WC()->payment_gateways()->payment_gateways();
    return isset($gateways['apiblockchain_apiusd']) ? $gateways['apiblockchain_apiusd'] : null;
}

function apiblockchain_apiusd_request($gateway, $method, $path, $body = null) {
    $url  = rtrim($gateway->get_option('api_url') ?: APIBLOCKCHAIN_APIUSD_DEFAULT_API, '/') . $path;
    $args = array(
        'method'  => $method,
        'timeout' => 20,
        'headers' => array(
            'Content-Type' => 'application/json',
            'X-API-Key'    => $gateway->get_option('api_key'),
        ),
    );
    if ($body !== null) {
        $args['body'] = wp_json_encode($body);
    }
    $response = wp_remote_request($url, $args);
    if (is_wp_error($response)) {
        return $response;
    }
    $code = (int) wp_remote_retrieve_response_code($response);
    $data = json_decode(wp_remote_retrieve_body($response), true);
    if ($code < 200 || $code >= 300) {
        $detail = is_array($data) ? ($data['error'] ?? ($data['detail'] ?? '')) : '';
        return new WP_Error('apiblockchain_http_' . $code, 'APIBlockchain responded ' . $code . ($detail ? ': ' . (is_string($detail) ? $detail : wp_json_encode($detail)) : ''));
    }
    return is_array($data) ? $data : array();
}

/**
 * Ask APIBlockchain whether the order's checkout is paid; if so, complete the order.
 * Paid means APIBlockchain verified the APIUSD transfer on-chain.
 */
function apiblockchain_apiusd_check_order($order) {
    if (!$order || $order->get_payment_method() !== 'apiblockchain_apiusd' || $order->is_paid()) {
        return;
    }
    $session_id = $order->get_meta(APIBLOCKCHAIN_APIUSD_META);
    $gateway    = apiblockchain_apiusd_gateway();
    if (!$session_id || !$gateway) {
        return;
    }
    $status = apiblockchain_apiusd_request($gateway, 'GET', '/session/' . rawurlencode($session_id) . '/status');
    if (is_wp_error($status) || ($status['status'] ?? '') !== 'paid') {
        return;
    }
    if (round((float) ($status['amount'] ?? 0), 2) < round((float) $order->get_total(), 2)) {
        $order->add_order_note('APIUSD checkout reported paid, but for a lower amount than the order total. Please check.');
        return;
    }
    $tx = $status['blockchain_tx_id'] ?? ($status['transaction_id'] ?? '');
    $order->add_order_note('APIUSD payment verified on-chain by APIBlockchain.' . ($tx ? ' Transaction: ' . $tx : ''));
    $order->payment_complete($tx);
}

// Customer comes back to the thank-you page
add_action('woocommerce_thankyou_apiblockchain_apiusd', function ($order_id) {
    apiblockchain_apiusd_check_order(wc_get_order($order_id));
});

// Customer closed the tab after paying: check open orders every 5 minutes (up to 2 days old)
add_filter('cron_schedules', function ($schedules) {
    $schedules['apiblockchain_five_minutes'] = array('interval' => 300, 'display' => 'Every 5 minutes');
    return $schedules;
});

add_action(APIBLOCKCHAIN_APIUSD_CRON, function () {
    if (!function_exists('wc_get_orders')) {
        return;
    }
    $orders = wc_get_orders(array(
        'payment_method' => 'apiblockchain_apiusd',
        'status'         => array('pending', 'on-hold'),
        'date_created'   => '>' . (time() - 2 * DAY_IN_SECONDS),
        'limit'          => 50,
    ));
    foreach ($orders as $order) {
        apiblockchain_apiusd_check_order($order);
    }
});

register_activation_hook(__FILE__, function () {
    if (!wp_next_scheduled(APIBLOCKCHAIN_APIUSD_CRON)) {
        wp_schedule_event(time() + 300, 'apiblockchain_five_minutes', APIBLOCKCHAIN_APIUSD_CRON);
    }
});

register_deactivation_hook(__FILE__, function () {
    wp_clear_scheduled_hook(APIBLOCKCHAIN_APIUSD_CRON);
});
