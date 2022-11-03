import init from 'react_native_mqtt';
import AsyncStorage from '@react-native-async-storage/async-storage';

const HOST = 'mqtt://broker.emqx.io'
const PORT = 1883
const WS_PORT = 8083 // websocket port

const DEFAULT_OPTIONS = {
    host: HOST,
    port: PORT,
    path: '/testTopic', // wtf is this path
    id: 'cs3237-lel'
};

// This initialises the client but does not connect client
const mqtt_client_init = (options) => {
    init({
        size: 10000,
        storageBackend: AsyncStorage,
        defaultExpires: 1000 * 3600 * 24, // 1000 days
        enableCache: true,
        reconnect: true,
        sync: {
          // nothing for now
        }
    })

    const client = new Paho.MQTT.Client(options.host, options.port, options.id);
    client.onConnectionLost = onConnectionLost;
    client.onMessageArrived = onMessageArrived;
    return client
}

// callback is what to do after client has connected
const connect = (client, callback) => {
    console.log("Connecting!")
    client.connect({
        onSuccess: onConnect,
        useSSL: false,
        timeout: 3,
        onFailure: () => console.log('Failed to connect!')
    });

    if (callback) {
        callback()
    }
    
}

const subscribeTopic = (client, topic, callback) => {
    client.subscribe(topic)
    if (callback) {
        callback()
    }
}

const sendMessage = (client, topic, message, callback) => {
    var mqtt_message = new Paho.MQTT.Message(options.id + ':' + this.state.message);
    mqtt_message.destinationName = topic;
    client.send(message);
    if (callback) {
        callback()
    }
}

const unsubscribeTopic = (client, topic, callback) => {
    client.unsubscribe(topic);
    if (callback) {
        callback()
    }
}

function onConnect() {
    console.log("onConnect");
}

function onConnectionLost(responseObject) {
    if (responseObject.errorCode !== 0) {
        console.log("onConnectionLost:"+responseObject.errorMessage);
}
}

function onMessageArrived(message) {
    console.log("onMessageArrived:"+message.payloadString);
}

export { DEFAULT_OPTIONS, mqtt_client_init, connect, subscribeTopic, sendMessage, unsubscribeTopic }