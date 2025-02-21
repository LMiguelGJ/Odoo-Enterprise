DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM ir_config_parameter WHERE key = 'database.expiration_date') THEN
        UPDATE ir_config_parameter
        SET value = '2030-03-30 00:00:00'
        WHERE key = 'database.expiration_date';
    ELSE
        INSERT INTO ir_config_parameter (key, value)
        VALUES ('database.expiration_date', '2030-03-30 00:00:00');
    END IF;
END $$;

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM ir_config_parameter WHERE key = 'database.enterprise_code') THEN
        UPDATE ir_config_parameter
        SET value = 'M22112861297726'
        WHERE key = 'database.enterprise_code';
    ELSE
        INSERT INTO ir_config_parameter (key, value)
        VALUES ('database.enterprise_code', 'M22112861297726');
    END IF;
END $$;

CREATE OR REPLACE FUNCTION prevent_delete_update() RETURNS trigger AS $$
BEGIN
    IF OLD.key IN ('database.expiration_date', 'database.enterprise_code') THEN
        RAISE EXCEPTION 'No se puede eliminar ni modificar la clave %', OLD.key;
    END IF;
    RETURN OLD;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER prevent_delete_update_trigger
BEFORE DELETE OR UPDATE ON ir_config_parameter
FOR EACH ROW
EXECUTE FUNCTION prevent_delete_update();
